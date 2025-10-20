import datetime
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .. import oauth, models, session

AVV_CLIENT_TOKEN = None
AVV_CLIENT_TOKEN_EXPIRY = None

def get_avv_client_token():
    global AVV_CLIENT_TOKEN
    global AVV_CLIENT_TOKEN_EXPIRY

    now = timezone.now()
    if AVV_CLIENT_TOKEN and AVV_CLIENT_TOKEN_EXPIRY and AVV_CLIENT_TOKEN_EXPIRY > now:
        return AVV_CLIENT_TOKEN

    r = session.post(oauth.PROVIDERS["avv"].token_url, data={
        "grant_type": "client_credentials",
        "client_id": oauth.PROVIDERS["avv"].client_id,
        "client_secret": oauth.PROVIDERS["avv"].client_secret,
    }, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    if not r.ok:
        return None

    data = r.json()
    AVV_CLIENT_TOKEN = data["access_token"]
    AVV_CLIENT_TOKEN_EXPIRY = now + datetime.timedelta(seconds=data["expires_in"])

    return AVV_CLIENT_TOKEN

@login_required
def avv_login(request):
    return render(request, "main/account/avv_login.html", {})


@login_required
def avv_account(request):
    avv_token = oauth.get_token(request.user.account, "avv")
    if not avv_token:
        return redirect('avv_login')

    account_oauth = models.AccountOAuth.objects.get(account=request.user.account, provider="avv")
    client_token = get_avv_client_token()

    r = session.get("https://zvp-hgs.avv.de/cxf/mobile_api/customer_rest/v2/customers/personal_data", headers={
        "Authorization": f"Bearer {avv_token}",
        "ClientToken": client_token,
        "deviceId": account_oauth.device_id,
        "language": "de",
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    data = r.json()

    return render(request, "main/account/avv.html", {
        "data": data,
        "tickets": account_oauth.tickets,
    })
