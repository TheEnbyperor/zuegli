import niquests
import typing
import bs4
import urllib.parse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .. import forms, eos, sbahn_berlin, models


def login(username: str, password: str) -> typing.Optional[typing.Tuple[str, str]]:
    device_id = eos.get_device_id()

    s = niquests.Session()

    r = s.get("https://sso.uptrade.de/realms/sbb/protocol/openid-connect/auth", params={
        "client_id": "eos-ts-sbahn-ber",
        "response_type": "code",
        "scope": "openid profile email offline_access",
        "redirect_uri": "https://sbahn-ber.tickeos.de/index.php/connect/request/1",
    }, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    r.raise_for_status()
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    form = soup.find("form", id="kc-form-login")
    action = form.attrs["action"]

    r = s.post(action, data={
        "username": username,
        "password": password,
    }, allow_redirects=False)
    if "Location" not in r.headers:
        return None
    loc = urllib.parse.urlparse(r.headers["Location"])
    qs = urllib.parse.parse_qs(loc.query)

    r = s.post("https://sbahn-ber.tickeos.de/index.php/mobileService/connect/authorize", json={
        "id": 1,
        "code": qs["code"][0],
    }, hooks={
        "pre_request": [lambda req: eos.sign_request(req, device_id, "sbb")],
    })
    auth_data = r.json()

    return f"Bearer {auth_data['access_token']}", device_id


@login_required
def sbahn_berlin_login(request):
    if request.method == "POST":
        form = forms.EOSLoginForm(request.POST)
        if form.is_valid():
            token = login(form.cleaned_data["username"], form.cleaned_data["password"])
            if not token:
                messages.error(request, "Login failed")
            else:
                messages.success(request, "Login successful")
                token, device_id = token
                models.AccountOAuth.objects.update_or_create(
                    account=request.user.account,
                    provider="sbahn_berlin",
                    defaults={
                        "token": token,
                        "device_id": device_id,
                    }
                )
                sbahn_berlin.update_sbahn_berlin_tickets.apply_async(args=(request.user.account.id,), queue="celery")
                return redirect("sbahn_berlin_account")
    else:
        form = forms.EOSLoginForm()

    return render(request, "main/account/sbahn_berlin_login.html", {
        "form": form,
    })


@login_required
def sbahn_berlin_account(request):
    if not request.user.account.is_sbahn_berlin_authenticated():
        return redirect("sbahn_berlin_login")

    account_oauth = models.AccountOAuth.objects.get(account=request.user.account, provider="sbahn_berlin")
    fields = eos.get_customer_account(request.user.account, "sbahn_berlin")

    return render(request, "main/account/sbahn_berlin.html", {
        "fields": fields,
        "tickets": account_oauth.tickets,
    })