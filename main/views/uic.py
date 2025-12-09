import urllib.parse
from django.conf import settings
from django.shortcuts import render


def read_uic_ndef(request):
    params = {}

    if request.user.is_authenticated:
        params["account"] = request.user.account.nfc_link_token

    params = urllib.parse.urlencode(params)
    ws_url = f"{settings.EXTERNAL_URL_BASE.replace('http', 'ws')}/ws/uic-ndef-nfc?{params}"
    params = urllib.parse.urlencode({
        "server": ws_url,
    })
    link_url = f"https://vdv-pkpass-nfc.magicalcodewit.ch/nfc?{params}"

    return render(request, "main/uic_ndef_read.html", {
        "link_url": link_url,
    })