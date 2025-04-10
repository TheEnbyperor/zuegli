import secrets
import base64
import hashlib
import urllib.parse
import binascii
import niquests
import jwt
import datetime
import bs4
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .. import models, forms, db_ticket

DB_ISSUER = "https://accounts.bahn.de/auth/realms/db"
AVV_AUTH_URL = "https://zvp-sso.avv.de/auth/realms/zvp/protocol/openid-connect/auth"
AVV_TOKEN_URL = "https://zvp-sso.avv.de/auth/realms/zvp/protocol/openid-connect/token"
AVV_CERTS_URL = "https://zvp-sso.avv.de/auth/realms/zvp/protocol/openid-connect/certs"

AVV_CLIENT_ID = "eosuptrade.avvshop"
AVV_CLIENT_SECRET = "a1d4b63f-189a-49ab-ba2d-119994a602a7"
AVV_REDIRECT_URI = "de.eosuptrade.avvshop://oauth2redirect"

AVV_CLIENT_TOKEN = None
AVV_CLIENT_TOKEN_EXPIRY = None

def get_avv_client_token():
    global AVV_CLIENT_TOKEN
    global AVV_CLIENT_TOKEN_EXPIRY

    now = timezone.now()
    if AVV_CLIENT_TOKEN and AVV_CLIENT_TOKEN_EXPIRY and AVV_CLIENT_TOKEN_EXPIRY > now:
        return AVV_CLIENT_TOKEN

    r = niquests.post(AVV_TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": AVV_CLIENT_ID,
        "client_secret": AVV_CLIENT_SECRET,
    }, headers={
        "User-Agent": "VDV PKPass q@magicalcodewit.ch"
    })
    if not r.ok:
        return None

    data = r.json()
    AVV_CLIENT_TOKEN = data["access_token"]
    AVV_CLIENT_TOKEN_EXPIRY = now + datetime.timedelta(seconds=data["expires_in"])

    return AVV_CLIENT_TOKEN

def get_avv_token(account: "models.Account"):
    now = timezone.now()
    if account.avv_token and account.avv_token_expires_at and \
            account.avv_token_expires_at > now:
        return account.avv_token
    elif account.avv_refresh_token:
        if account.avv_refresh_token_expires_at and account.avv_refresh_token_expires_at > now:
            r = niquests.post(AVV_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "client_id": AVV_CLIENT_ID,
                "client_secret": AVV_CLIENT_SECRET,
                "refresh_token": account.avv_refresh_token,
            }, headers={
                "User-Agent": "VDV PKPass q@magicalcodewit.ch"
            })
            if not r.ok:
                return None

            data = r.json()
            account.avv_token = data["access_token"]
            account.avv_token_expires_at = now + datetime.timedelta(seconds=data["expires_in"])
            account.avv_refresh_token = data["refresh_token"]
            account.avv_refresh_token_expires_at = now + datetime.timedelta(seconds=data["refresh_expires_in"])
            account.save()
            return account.avv_token
        else:
            return None
    else:
        return None

@login_required
def avv_login(request):
    return render(request, "main/account/avv_login.html", {})


@login_required
def avv_logout(request):
    request.user.account.avv_token = None
    request.user.account.avv_token_expires_at = None
    request.user.account.avv_refresh_token = None
    request.user.account.avv_refresh_token_expires_at = None
    request.user.account.save()
    messages.add_message(request, messages.SUCCESS, "Successfully logged out")
    return redirect("account")


@login_required
def avv_login_start(request):
    code_verifier = secrets.token_hex(32)
    session_state = secrets.token_hex(32)
    request.session["avv_code_verifier"] = code_verifier
    request.session["avv_session_state"] = session_state
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().replace("=", "")
    params = urllib.parse.urlencode({
        "client_id": AVV_CLIENT_ID,
        "redirect_uri": AVV_REDIRECT_URI,
        "response_type": "code",
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "state": session_state,
        "scope": "offline_access",
    })
    return redirect(f"{AVV_AUTH_URL}?{params}")

@login_required
def avv_login_callback(request):
    if "url" not in request.GET or \
            "avv_code_verifier" not in request.session or \
            "avv_session_state" not in request.session:
        return redirect('avv_login')

    try:
        url = base64.urlsafe_b64decode(request.GET["url"]).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        messages.error(request, "Invalid login response")
        return redirect('avv_login')

    response_url = urllib.parse.urlparse(url)

    if response_url.scheme != "de.eosuptrade.avvshop":
        messages.error(request, "Invalid login response")
        return redirect('avv_login')

    if response_url.netloc != "oauth2redirect":
        messages.error(request, "Invalid login response")
        return redirect('avv_login')

    response_params = urllib.parse.parse_qs(response_url.query)

    if "error" in response_params:
        messages.error(request, f"Login error - {response_params.get('error_description', '')}")
        return redirect('avv_login')

    code = response_params.get("code", [""])[0]
    avv_session_state = response_params.get("session_state", [""])[0]
    code_verifier = request.session.pop("avv_code_verifier")
    session_state = request.session.pop("avv_session_state")

    if response_params.get("state", [""])[0] != session_state:
        messages.error(request, "Invalid login response")
        return redirect('avv_login')

    r = niquests.post(AVV_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "client_id": AVV_CLIENT_ID,
        "client_secret": AVV_CLIENT_SECRET,
        "redirect_uri": AVV_REDIRECT_URI,
        "code": code,
        "code_verifier": code_verifier,
    }, headers={
        "User-Agent": "VDV PKPass (q@magicalcodewit.ch)"
    })
    data = r.json()
    if not r.ok:
        messages.error(request, f"Login failed - {data.get('error_description', '')}")
        return redirect('avv_login')

    if data.get("session_state") != avv_session_state:
        messages.error(request, "Invalid login response")
        return redirect('avv_login')

    auth_token = data.get("access_token", None)
    auth_token_expires_at = timezone.now() + datetime.timedelta(seconds=data.get("expires_in", 0))
    refresh_token = data.get("refresh_token", None)
    refresh_token_expires_at = timezone.now() + datetime.timedelta(seconds=data.get("refresh_expires_in", 0))

    request.user.account.avv_token = auth_token
    request.user.account.avv_token_expires_at = auth_token_expires_at
    request.user.account.avv_refresh_token = refresh_token
    request.user.account.avv_refresh_token_expires_at = refresh_token_expires_at
    request.user.account.avv_device_id = secrets.token_hex(16)
    request.user.account.save()

    return redirect('account')

@login_required
def avv_account(request):
    avv_token = get_avv_token(request.user.account)
    if not avv_token:
        return redirect('avv_login')

    client_token = get_avv_client_token()

    r = niquests.get("https://zvp-hgs.avv.de/cxf/mobile_api/customer_rest/v2/customers/personal_data", headers={
        "Authorization": f"Bearer {avv_token}",
        "ClientToken": client_token,
        "deviceId": request.user.account.avv_device_id,
        "language": "de",
        "User-Agent": "VDV PKPass (q@magicalcodewit.ch)"
    })
    data = r.json()

    return render(request, "main/account/avv.html", {
        "data": data,
        "tickets": request.user.account.avv_tickets,
    })