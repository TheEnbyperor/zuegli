from django.shortcuts import render
from . import apple_api, passes, account, db, db_abo, saarvv, api, sncb, metrics, ical, util, sbahn_berlin, nfc, vdv, avv


def page_not_found(request, exception):
    return render(request, "main/404.html", {
        "exception": exception,
    }, status=404)