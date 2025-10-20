import dataclasses
import base64
import typing
import urllib.parse
import datetime
import secrets
import hashlib
import jwt
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from . import models, session

DB_CERTS_URL = "https://accounts.bahn.de/auth/realms/db/protocol/openid-connect/certs"
DB_ISSUER = "https://accounts.bahn.de/auth/realms/db"


@dataclasses.dataclass
class OAuthProvider:
    client_id: str
    scope: str
    login_url: str
    redirect_url: str
    token_url: str
    client_secret: typing.Optional[str] = None
    login_done: typing.Optional[typing.Callable] = None

def logout(request, provider: str):
    oauth = models.AccountOAuth.objects.filter(account=request.user.account, provider=provider).first()
    if oauth:
        oauth.token = None
        oauth.token_expires_at = None
        oauth.refresh_token = None
        oauth.refresh_token_expires_at = None
        oauth.save()

    messages.add_message(request, messages.SUCCESS, "Successfully logged out")
    return redirect("account")

def login_start(request, provider: str):
    code_verifier = secrets.token_hex(32)
    session_state = secrets.token_hex(32)
    request.session[f"oauth_{provider}_code_verifier"] = code_verifier
    request.session[f"oauth_{provider}_session_state"] = session_state
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().replace("=", "")
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": PROVIDERS[provider].client_id,
        "redirect_uri": PROVIDERS[provider].redirect_url,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": PROVIDERS[provider].scope,
        "state": session_state,
    })
    return redirect(f"{PROVIDERS[provider].login_url}?{params}")

def login_callback(request, provider: str, url: str):
    if f"oauth_{provider}_code_verifier" not in request.session or f"oauth_{provider}_session_state" not in request.session:
        return redirect(f"{provider}_login")

    response_url = urllib.parse.urlparse(url)
    redirect_uri = urllib.parse.urlparse(PROVIDERS[provider].redirect_url)

    if response_url.scheme != redirect_uri.scheme:
        messages.error(request, "Invalid login response")
        return redirect(f"{provider}_login")

    if response_url.netloc != redirect_uri.netloc:
        messages.error(request, "Invalid login response")
        return redirect(f"{provider}_login")

    if response_url.path != redirect_uri.path:
        messages.error(request, "Invalid login response")
        return redirect(f"{provider}_login")

    response_params = urllib.parse.parse_qs(response_url.query)

    if "error" in response_params:
        messages.error(request, f"Login error - {response_params.get('error_description', '')}")
        return redirect(f"{provider}_login")

    code = response_params.get("code", [""])[0]
    code_verifier = request.session.pop(f"oauth_{provider}_code_verifier")
    session_state = request.session.pop(f"oauth_{provider}_session_state")

    if response_params.get("state", [""])[0] != session_state:
        messages.error(request, "Invalid login response")
        return redirect(f"{provider}_login")

    data = {
        "grant_type": "authorization_code",
        "client_id": PROVIDERS[provider].client_id,
        "redirect_uri": PROVIDERS[provider].redirect_url,
        "code": code,
        "code_verifier": code_verifier,
    }

    if PROVIDERS[provider].client_secret:
        data["client_secret"] = PROVIDERS[provider].client_secret

    r = session.post(PROVIDERS[provider].token_url, data=data, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    data = r.json()

    if not r.ok:
        messages.error(request, f"Login failed - {data.get('error_description', '')}")
        return redirect(f"{provider}_login")

    if "session_state" in response_params and data.get("session_state") != response_params["session_state"][0]:
            messages.error(request, "Invalid login response")
            return redirect(f"{provider}_login")

    auth_token = data.get("access_token", None)
    auth_token_expires_at = timezone.now() + datetime.timedelta(seconds=data["expires_in"])
    refresh_token = data.get("refresh_token", None)
    if t := data.get("refresh_expires_in"):
        refresh_token_expires_at = timezone.now() + datetime.timedelta(seconds=t)
    else:
        refresh_token_expires_at = None

    oauth, _ = models.AccountOAuth.objects.update_or_create(
        account=request.user.account,
        provider=provider,
        defaults={
            "token": auth_token,
            "token_expires_at": auth_token_expires_at,
            "refresh_token": refresh_token,
            "refresh_token_expires_at": refresh_token_expires_at,
        }
    )
    if PROVIDERS[provider].login_done:
        PROVIDERS[provider].login_done(oauth)
    request.user.account.save()

    return redirect("account")

def get_token(account: "models.Account", provider: str):
    now = timezone.now()
    oauth = models.AccountOAuth.objects.filter(account=account, provider=provider).first()
    if not oauth:
        return None

    if oauth.token and oauth.token_expires_at and oauth.token_expires_at - datetime.timedelta(minutes=2) > now:
        return oauth.token
    elif oauth.refresh_token:
        if not oauth.refresh_token_expires_at or oauth.refresh_token_expires_at - datetime.timedelta(minutes=2) > now :
            data = {
                "grant_type": "refresh_token",
                "client_id": PROVIDERS[provider].client_id,
                "refresh_token": oauth.refresh_token,
            }
            if PROVIDERS[provider].client_secret:
                data["client_secret"] = PROVIDERS[provider].client_secret
            r = session.post(PROVIDERS[provider].token_url, data=data, headers={
                "User-Agent": "Zuegli (q@magicalcodewit.ch)"
            })
            if not r.ok:
                return None

            data = r.json()
            oauth.token = data["access_token"]
            oauth.token_expires_at = now + datetime.timedelta(seconds=data["expires_in"])
            oauth.refresh_token = data.get("refresh_token", None)
            if "refresh_expires_in" in data:
                oauth.refresh_token_expires_at = now + datetime.timedelta(seconds=data["refresh_expires_in"])
            else:
                oauth.refresh_token_expires_at = None
            oauth.save()
            return oauth.token

    return None

def avv_login_done(oauth: "models.AccountOAuth"):
    oauth.device_id = secrets.token_hex(16)
    oauth.save()

def db_login_done(oauth: "models.AccountOAuth"):
    jwks_client = jwt.PyJWKClient(DB_CERTS_URL)
    header = jwt.get_unverified_header(oauth.token)
    key = jwks_client.get_signing_key(header["kid"]).key
    auth_data = jwt.decode(
        oauth.token, key, [header["alg"]],
        issuer=DB_ISSUER,
        options={
            "verify_aud": False
        },
        leeway=60,
    )
    oauth.extra_data["account_id"] = auth_data.get("kundenkontoid")
    oauth.save()


PROVIDERS = {
    "db": OAuthProvider(
        client_id="kf_mobile",
        redirect_url="dbnav://dbnavigator.bahn.de/auth",
        scope="offline_access",
        login_url="https://accounts.bahn.de/auth/realms/db/protocol/openid-connect/auth",
        token_url="https://accounts.bahn.de/auth/realms/db/protocol/openid-connect/token",
        login_done=db_login_done,
    ),
    "bahnbonus": OAuthProvider(
        client_id="fe_bb_app",
        redirect_url="bahnbonus://authentication/redirect",
        scope="offline_access openid self-impersonation",
        login_url="https://accounts.bahn.de/auth/realms/db/protocol/openid-connect/auth",
        token_url="https://accounts.bahn.de/auth/realms/db/protocol/openid-connect/token"
    ),
    "avv": OAuthProvider(
        client_id="eosuptrade.avvshop",
        client_secret="a1d4b63f-189a-49ab-ba2d-119994a602a7",
        redirect_url="de.eosuptrade.avvshop://oauth2redirect",
        scope="offline_access",
        login_url="https://zvp-sso.avv.de/auth/realms/zvp/protocol/openid-connect/auth",
        token_url="https://zvp-sso.avv.de/auth/realms/zvp/protocol/openid-connect/token",
        login_done=avv_login_done
    ),
    "vestische": OAuthProvider(
        client_id="vestische",
        redirect_url="vestische://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://ticketshop.vestische.de/Identity/v2/connect/authorize/callback",
        token_url="https://ticketshop.vestische.de/Identity/v2/connect/token"
    ),
    "nrway": OAuthProvider(
        client_id="bvr",
        redirect_url="bvr://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://nrway.dbregiobus-nrw.de/Identity/v2/connect/authorize/callback",
        token_url="https://nrway.dbregiobus-nrw.de/Identity/v2/connect/token",
    ),
    "sobus": OAuthProvider(
        client_id="sobus",
        redirect_url="sobus://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://ticketshop.sobus.net/Identity/v2/connect/authorize/callback",
        token_url="https://ticketshop.sobus.net/Identity/v2/connect/token",
    ),
    "vrr": OAuthProvider(
        client_id="classic",
        redirect_url="classic://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://vrr-db-ticketshop.de/Identity/v2/connect/authorize/callback",
        token_url="https://vrr-db-ticketshop.de/Identity/v2/connect/token",
    ),
    "bogestra": OAuthProvider(
        client_id="bogestra",
        redirect_url="bogestra://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://ticketservice.bogestra.de/Identity/v2/connect/authorize/callback",
        token_url="https://ticketservice.bogestra.de/Identity/v2/connect/token",
    ),
    "dsw21": OAuthProvider(
        client_id="dsw21",
        redirect_url="dsw21://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://ticketshop.dsw21.de/Identity/v2/connect/authorize/callback",
        token_url="https://ticketshop.dsw21.de/Identity/v2/connect/token",
    ),
    "dvg": OAuthProvider(
        client_id="dvg",
        redirect_url="dvg://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://mydvgbusundbahn.dvg-duisburg.de/Identity/v2/connect/authorize/callback",
        token_url="https://mydvgbusundbahn.dvg-duisburg.de/Identity/v2/connect/token",
    ),
    "hagen": OAuthProvider(
        client_id="hst",
        redirect_url="hst://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://ticketshop.strassenbahn-hagen.de/Identity/v2/connect/authorize/callback",
        token_url="https://ticketshop.strassenbahn-hagen.de/Identity/v2/connect/token",
    ),
    "hcr": OAuthProvider(
        client_id="hcr",
        redirect_url="hcr://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://shop.hcr-herne.de/Identity/v2/connect/authorize/callback",
        token_url="https://shop.hcr-herne.de/Identity/v2/connect/token",
    ),
    "moebus": OAuthProvider(
        client_id="moebus",
        redirect_url="moebus://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://tickets-moebus.new.de/Identity/v2/connect/authorize/callback",
        token_url="https://tickets-moebus.new.de/Identity/v2/connect/token",
    ),
    "viersen": OAuthProvider(
        client_id="viersen",
        redirect_url="viersen://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://tickets-viersen.new.de/Identity/v2/connect/authorize/callback",
        token_url="https://tickets-viersen.new.de/Identity/v2/connect/token",
    ),
    "niag": OAuthProvider(
        client_id="niag",
        redirect_url="niag://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://niag-ticketshop.de/Identity/v2/connect/authorize/callback",
        token_url="https://niag-ticketshop.de/Identity/v2/connect/token",
    ),
    "ruhrbahn-essen": OAuthProvider(
        client_id="evag",
        redirect_url="evag://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://ticketshop.ruhrbahn.de/Identity/v2/connect/authorize/callback",
        token_url="https://ticketshop.ruhrbahn.de/Identity/v2/connect/token",
    ),
    "ruhrbahn-muellheim": OAuthProvider(
        client_id="mvg",
        redirect_url="mvg://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://ticketshop.ruhrbahn.de/Identity/v2/connect/authorize/callback",
        token_url="https://ticketshop.ruhrbahn.de/Identity/v2/connect/token",
    ),
    "dormagen": OAuthProvider(
        client_id="sdg",
        redirect_url="sdg://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://ticketshop.svgd.de/Identity/v2/connect/authorize/callback",
        token_url="https://ticketshop.svgd.de/Identity/v2/connect/token",
    ),
    "neuss": OAuthProvider(
        client_id="swn",
        redirect_url="swn://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://tickets.stadtwerke-neuss.de/Identity/v2/connect/authorize/callback",
        token_url="https://tickets.stadtwerke-neuss.de/Identity/v2/connect/token",
    ),
    "remscheid": OAuthProvider(
        client_id="swr",
        redirect_url="swr://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://sr-ticketshop.stadtwerke-remscheid.de/Identity/v2/connect/authorize/callback",
        token_url="https://sr-ticketshop.stadtwerke-remscheid.de/Identity/v2/connect/token",
    ),
    "oberhausen": OAuthProvider(
        client_id="stoag",
        redirect_url="stoag://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://ticketshop.stoag.de/Identity/v2/connect/authorize/callback",
        token_url="https://ticketshop.stoag.de/Identity/v2/connect/token",
    ),
    "swk": OAuthProvider(
        client_id="swk",
        redirect_url="swk://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://tickets.swk.de/Identity/v2/connect/authorize/callback",
        token_url="https://tickets.swk.de/Identity/v2/connect/token",
    ),
    "ver": OAuthProvider(
        client_id="ver",
        redirect_url="ver://oauth/callback",
        scope="ticketing offline_access",
        login_url="https://etarif-ticketshop.ver-kehr.de/Identity/v2/connect/authorize/callback",
        token_url="https://etarif-ticketshop.ver-kehr.de/Identity/v2/connect/token",
    ),
}