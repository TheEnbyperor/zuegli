import niquests
import typing
import bs4
import urllib.parse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .. import forms, eos, sbahn_berlin


def login(username: str, password: str) -> typing.Optional[typing.Tuple[str, str]]:
    device_id = eos.get_device_id()

    s = niquests.Session()

    r = s.get("https://sso.uptrade.de/realms/sbb/protocol/openid-connect/auth", params={
        "client_id": "eos-ts-sbahn-ber",
        "response_type": "code",
        "scope": "openid profile email offline_access",
        "redirect_uri": "https://sbahn-ber.tickeos.de/index.php/connect/request/1",
    }, headers={
        "User-Agent": "VDV PKPass (q@magicalcodewit.ch)"
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

    return auth_data["access_token"], device_id


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
                request.user.account.sbahn_berlin_token = token
                request.user.account.sbahn_berlin_device_id = device_id
                request.user.account.save()
                sbahn_berlin.update_sbahn_berlin_tickets(request.user.account)
                return redirect("sbahn_berlin_account")
    else:
        form = forms.EOSLoginForm()

    return render(request, "main/account/sbahn_berlin_login.html", {
        "form": form,
    })


@login_required
def sbahn_berlin_logout(request):
    request.user.account.sbahn_berlin_token = None
    request.user.account.sbahn_berlin_device_id = None
    request.user.account.save()
    messages.add_message(request, messages.SUCCESS, "Successfully logged out")
    return redirect("account")


@login_required
def sbahn_berlin_account(request):
    if not request.user.account.sbahn_berlin_token:
        return redirect("sbahn_berlin_login")

    r = niquests.post(f"https://sbahn-ber.tickeos.de/index.php/mobileService/customer/fields", json={}, hooks={
        "pre_request": [lambda req: eos.sign_request(req, request.user.account.sbahn_berlin_device_id, "sbb")],
    }, headers={
        "Authorization": f"Bearer {request.user.account.sbahn_berlin_token}"
    })
    r.raise_for_status()
    data = r.json()

    fields = {f["name"]: eos.map_customer_field(f) for b in data["layout_blocks"] for f in b["fields"]}

    return render(request, "main/account/sbahn_berlin.html", {
        "fields": fields,
        "tickets": request.user.account.sbahn_berlin_tickets,
    })