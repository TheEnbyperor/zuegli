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

PROVIDERS = {
    "vestische": {
        "client_id": "vestische",
        "redirect_uri": "vestische://oauth/callback",
        "login_url": "https://ticketshop.vestische.de/authentication/login",
        "token_url": "https://ticketshop.vestische.de/Identity/v2/connect/token",
    }
}


@login_required
def vestische_login(request):
    return render(request, "main/account/vestische_login.html", {})

@login_required
def vestische_login_start(request):
    return login_start(request, "vestische")

@login_required
def vestische_login_callback(request):
    return login_callback(request, "vestische")

@login_required
def vestische_logout(request):
    return logout(request, "vestische")


def logout(request, provider: str):
    request.user.account.oauth.filter(provider=provider).delete()
    request.user.account.save()
    messages.add_message(request, messages.SUCCESS, "Successfully logged out")
    return redirect("account")


def login_start(request, provider: str):
    code_verifier = secrets.token_hex(32)
    session_state = secrets.token_hex(32)
    request.session[f"vrr_{provider}_code_verifier"] = code_verifier
    request.session[f"vrr_{provider}_session_state"] = session_state
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().replace("=", "")
    login_params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": PROVIDERS[provider]["client_id"],
        "redirect_uri": PROVIDERS[provider]["redirect_uri"],
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "lang": "de",
        "scope": "ticketing offline_access",
        "state": session_state,
    })
    params = urllib.parse.urlencode({
        "lang": "de",
        "client": PROVIDERS[provider]["client_id"],
        "organization": "vrr",
        "clientUsage": "app",
        "appType": "C5",
        "returnUrl": f"/Identity/v2/connect/authorize/callback?{login_params}",
        "clientMode": "dark"
    })
    auth_url = PROVIDERS[provider]["login_url"]
    return redirect(f"{auth_url}?{params}")

def login_callback(request, provider: str):
    if "url" not in request.GET or \
            f"vrr_{provider}_code_verifier" not in request.session or \
            f"vrr_{provider}_session_state" not in request.session:
        return redirect(f"{provider}_login")

    try:
        url = base64.urlsafe_b64decode(request.GET["url"]).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        messages.error(request, "Invalid login response")
        return redirect(f"{provider}_login")

    response_url = urllib.parse.urlparse(url)
    redirect_uri = urllib.parse.urlparse(PROVIDERS[provider]["redirect_uri"])

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
    code_verifier = request.session.pop(f"vrr_{provider}_code_verifier")
    session_state = request.session.pop(f"vrr_{provider}_session_state")

    if response_params.get("state", [""])[0] != session_state:
        messages.error(request, "Invalid login response")
        return redirect(f"{provider}_login")

    r = niquests.post(PROVIDERS[provider]["token_url"], data={
        "grant_type": "authorization_code",
        "client_id": PROVIDERS[provider]["client_id"],
        "redirect_uri": PROVIDERS[provider]["redirect_uri"],
        "code": code,
        "code_verifier": code_verifier,
    }, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    data = r.json()

    if not r.ok:
        messages.error(request, f"Login failed - {data.get('error_description', '')}")
        return redirect(f"{provider}_login")

    auth_token = data.get("access_token", None)
    auth_token_expires_at = timezone.now() + datetime.timedelta(seconds=data["expires_in"])
    refresh_token = data.get("refresh_token", None)
    if "refresh_expires_in" in data:
        refresh_token_expires_at = timezone.now() + datetime.timedelta(seconds=data["refresh_expires_in"])
    else:
        refresh_token_expires_at = None

    models.AccountOAuth.objects.update_or_create(
        account=request.user.account,
        provider=provider,
        defaults={
            "token": auth_token,
            "token_expires_at": auth_token_expires_at,
            "refresh_token": refresh_token,
            "refresh_token_expires_at": refresh_token_expires_at,
        }
    )
    request.user.account.save()

    return redirect("account")

def get_token(account: "models.Account", provider: str):
    now = timezone.now()
    oauth = models.AccountOAuth.objects.filter(account=account, provider=provider).first()
    if not oauth:
        return None

    if oauth.token and oauth.token_expires_at and oauth.token_expires_at > now:
        return oauth.token
    elif oauth.refresh_token:
        if not oauth.refresh_token_expires_at or oauth.refresh_token_expires_at > now:
            r = niquests.post(PROVIDERS[provider]["token_url"], data={
                "grant_type": "refresh_token",
                "client_id": PROVIDERS[provider]["client_id"],
                "refresh_token": oauth.refresh_token,
            }, headers={
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
