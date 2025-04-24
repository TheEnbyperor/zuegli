import niquests
import typing
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .. import forms, eos, saarvv, models


def login(username: str, password: str) -> typing.Optional[typing.Tuple[str, str]]:
    device_id = eos.get_device_id()
    r = niquests.post(f"https://saarvv.tickeos.de/index.php/mobileService/login", json={
        "credentials": {
            "password": password,
            "username": username,
        }
    }, hooks={
        "pre_request": [lambda req: eos.sign_request(req, device_id, "saarvv")],
    })
    if not r.ok:
        return None
    auth_data = r.json()
    access_token_data = next(filter(lambda t: t["name"] == "tickeos_access_token", auth_data["authorization_types"]), None)
    if not access_token_data:
        return None
    access_token = "{} {}".format(access_token_data["header"]["type"], access_token_data["header"]["value"])
    return access_token, device_id


@login_required
def saarvv_login(request):
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
                    provider="saarvv",
                    defaults={
                        "token": token,
                        "device_id": device_id,
                    }
                )
                saarvv.update_saarvv_tickets(request.user.account)
                return redirect("saarvv_account")
    else:
        form = forms.EOSLoginForm()

    return render(request, "main/account/saarvv_login.html", {
        "form": form,
    })

@login_required
def saarvv_account(request):
    if not request.user.account.is_saarvv_authenticated():
        return redirect("saarvv_login")

    account_oauth = models.AccountOAuth.objects.get(account=request.user.account, provider="saarvv")
    fields = eos.get_customer_account(request.user.account, "saarvv", "https://saarvv.tickeos.de", "saarvv")

    return render(request, "main/account/saarvv.html", {
        "fields": fields,
        "tickets": account_oauth.tickets,
    })