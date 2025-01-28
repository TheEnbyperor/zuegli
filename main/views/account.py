import secrets
import niquests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, reverse
from . import db

@login_required
def index(request):
    calendar_url = reverse("account_calendar", args=(request.user.account.calendar_token,))

    return render(request, "main/account/index.html", {
        "user": request.user,
        "tickets": request.user.account.tickets.order_by("-last_updated"),
        "calendar_url": f"{settings.EXTERNAL_URL_BASE}{calendar_url}"
    })

@login_required
def db_account(request):
    context = {}
    if db_token := db.get_db_token(request.user.account):
        r = niquests.post(f"https://app.vendo.noncd.db.de/mob/kundenkonten/{request.user.account.db_account_id}", headers={
            "Authorization": f"Bearer {db_token}",
            "Accept": "application/x.db.vendo.mob.kundenkonto.v6+json",
            "X-Correlation-ID": secrets.token_hex(16),
            "User-Agent": "VDV PKPass q@magicalcodewit.ch"
        })
        if not r.ok:
            messages.add_message(request, messages.ERROR, "Failed to get DB account information")
        else:
            data = r.json()
            context["db_account"] = data

        r = niquests.get(f"https://app.vendo.noncd.db.de/mob/kundenkonten/{request.user.account.db_account_id}/bbStatus", headers={
            "Authorization": f"Bearer {db_token}",
            "Accept": "application/x.db.vendo.mob.bahnbonus.v1+json",
            "X-Correlation-ID": secrets.token_hex(16),
            "User-Agent": "VDV PKPass q@magicalcodewit.ch"
        })
        if not r.ok:
            messages.add_message(request, messages.ERROR, "Failed to get BahnBonus information")
        else:
            data = r.json()
            context["db_bb_status"] = data
    else:
        return redirect('account')

    return render(request, "main/account/db.html", context)

