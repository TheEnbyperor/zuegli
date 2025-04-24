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
from .. import models, forms, db_ticket, oauth

DB_AUTH_URL = "https://accounts.bahn.de/auth/realms/db/protocol/openid-connect/auth"
DB_TOKEN_URL = "https://accounts.bahn.de/auth/realms/db/protocol/openid-connect/token"

@login_required
def db_login(request):
    return render(request, "main/account/db_login.html", {})


@login_required
def bahnbonus_login(request):
    return render(request, "main/account/bahnbonus_login.html", {})


@login_required
def db_account(request):
    db_token = oauth.get_token(request.user.account, "db")
    if not db_token:
        return redirect('db_login')

    account_oauth = models.AccountOAuth.objects.get(account=request.user.account, provider="db")
    account_id = account_oauth.extra_data["account_id"]

    context = {}
    r = niquests.post(f"https://app.vendo.noncd.db.de/mob/kundenkonten/{account_id}", headers={
        "Authorization": f"Bearer {db_token}",
        "Accept": "application/x.db.vendo.mob.kundenkonto.v6+json",
        "X-Correlation-ID": secrets.token_hex(16),
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    if not r.ok:
        messages.add_message(request, messages.ERROR, "Failed to get DB account information")
    else:
        data = r.json()
        context["db_account"] = data

    r = niquests.get(f"https://app.vendo.noncd.db.de/mob/kundenkonten/{account_id}/bbStatus", headers={
        "Authorization": f"Bearer {db_token}",
        "Accept": "application/x.db.vendo.mob.bahnbonus.v1+json",
        "X-Correlation-ID": secrets.token_hex(16),
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    if not r.ok:
        messages.add_message(request, messages.ERROR, "Failed to get BahnBonus information")
    else:
        data = r.json()
        context["db_bb_status"] = data

    return render(request, "main/account/db.html", context)

@login_required
def db_add_ticket(request):
    initial = {
        "surname": request.user.last_name,
    }

    if request.method == "POST":
        form = forms.DBTicketForm(request.POST, initial=initial)
        if form.is_valid():
            booking_number = form.cleaned_data["booking_number"]
            surname = form.cleaned_data["surname"]
            r = niquests.post(f"https://app.vendo.noncd.db.de/mob/auftrag/{booking_number}/manuellLaden", headers={
                "Accept": "application/x.db.vendo.mob.auftraege.v7+json",
                "Content-Type": "application/x.db.vendo.mob.auftraege.v7+json",
                "X-Correlation-ID": secrets.token_hex(16),
                "User-Agent": "Zuegli (q@magicalcodewit.ch)",
            }, json={
                "nachname": surname,
            })
            if r.status_code == 404:
                messages.error(request, "Ticket not found")
            elif not r.ok:
                messages.error(request, "Failed to fetch ticket")
            else:
                if not request.user.last_name:
                    request.user.last_name = surname
                    request.user.save()

                data = r.json()
                added = []
                for ticket in data["auftragsbezogeneReisen"]:
                    ticket_data = base64.urlsafe_b64decode(ticket["ticket"]["ticket"] + '==')
                    ticket_layout = bs4.BeautifulSoup(ticket_data, 'html.parser')
                    barcode_elm = ticket_layout.find("img", attrs={
                        "id": "ticketbarcode"
                    }, recursive=True)
                    if not barcode_elm:
                        continue

                    ticket_obj = db_ticket.update_from_img_elm(barcode_elm, request.user.account)
                    if ticket_obj:
                        added.append(ticket_obj)

                if len(added) == 1:
                    return redirect('ticket', added[0].id)
                else:
                    messages.success(request, f"Successfully added {len(added)} ticket(s)")
                    return redirect('account')
    else:
        form = forms.DBTicketForm(initial=initial)

    return render(request, "main/account/db_ticket.html", {
        "form": form,
    })