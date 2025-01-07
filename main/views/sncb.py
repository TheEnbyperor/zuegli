import niquests
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from .. import forms, aztec


@login_required
def sncb_add_ticket(request):
    initial = {
        "email": request.user.email
    }

    if request.method == "POST":
        form = forms.SNCBTicketForm(request.POST, initial=initial)
        if form.is_valid():
            pnr = form.cleaned_data["pnr"]
            email = form.cleaned_data["email"]
            r = niquests.get(f"https://api.b-europe.com/dossier-details/{pnr}", params={
                "Context": "Upload",
                "Control": email
            }, headers={
                "API-Version": "8.1",
                "API-Key": settings.SNCB_API_KEY,
                "Accept-Language": "EN_GB",
                "Content-Type": "application/json",
            })
            if not r.ok:
                messages.error(request, "Failed to fetch ticket - check the PNR and email")
            else:
                data = json.loads(r.text)
                added = 0
                for segment in data["Dossier"]["TravelSegments"]:
                    for ticket in segment["Tickets"]:
                        barcode_url = f"https://www.bene-system.com{ticket['BarcodeURL']}"
                        br = niquests.get(barcode_url)
                        if not br.ok:
                            messages.warning(request, "Failed to fetch ticket barcode, ticket segment skipped")
                            continue

                        try:
                            barcode_data = aztec.decode(r.content)
                        except aztec.AztecError as e:
                            messages.warning(request, f"Error decoding barcode image: {e} - ticket segment skipped")
                            continue

                        try:
                            ticket_obj = ticket.update_from_subscription_barcode(barcode_data, account=request.user.account)
                            ticket_obj.save()
                        except ticket.TicketError as e:
                            messages.warning(request, f"Error decoding barcode ticket: {e} - ticket segment skipped")
                            return

                        added += 1

                messages.success(request, f"Successfully added {added} ticket(s)")
                return redirect('account')
    else:
        form = forms.SNCBTicketForm(initial=initial)

    return render(request, "main/account/sncb_ticket.html", {
        "form": form,
    })
