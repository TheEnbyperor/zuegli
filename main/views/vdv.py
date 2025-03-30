import urllib.parse
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from .. import models


def read_smartcard(request):
    params = {}

    if request.user.is_authenticated:
        params["account"] = request.user.account.nfc_link_token

    params = urllib.parse.urlencode(params)
    ws_url = f"{settings.EXTERNAL_URL_BASE.replace('http', 'ws')}/ws/vdv-nfc?{params}"
    params = urllib.parse.urlencode({
        "server": ws_url,
    })
    link_url = f"https://vdv-pkpass-nfc.magicalcodewit.ch/nfc?{params}"

    return render(request, "main/vdv_read.html", {
        "link_url": link_url,
    })


def view_smartcard(request, pk):
    smartcard_obj = get_object_or_404(models.VDVSmartcard, id=pk)

    return render(request, "main/vdv_smartcard.html", {
        "smartcard": smartcard_obj,
    })