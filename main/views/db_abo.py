import uuid
import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .. import forms, models, db_abo, session


@login_required
def view_db_abo(request):
    subscriptions = models.DBSubscription.objects.filter(account=request.user.account)

    return render(request, "main/account/db_abo.html", {
        "subscriptions": subscriptions
    })


@login_required
def new_abo(request):
    initial = {
        "surname": request.user.last_name,
    }

    already_present = False
    if request.method == "POST":
        form = forms.DBAboForm(request.POST, initial=initial)
        if form.is_valid():
            abo_data = {
                "abonummer": form.cleaned_data["subscription_number"],
            }
            if form.cleaned_data["surname"]:
                abo_data["nachname"] = form.cleaned_data["surname"]
            if form.cleaned_data["date_of_birth"]:
                abo_data["geburtsdatum"] = form.cleaned_data["date_of_birth"].strftime("%d.%m.%Y")
            if request.POST.get("action") == "remove":
                r = session.post("https://dig-aboprod.noncd.db.de/aboticket/changedevice", json=abo_data, headers={
                    "X-User-Agent": "com.deutschebahn.abo.navigatorV2.modul",
                    "X-Api-Version": "10",
                    "X-Unique-ID": str(uuid.uuid4()),
                    "User-Agent": "Zuegli (q@magicalcodewit.ch)"
                })
                if r.status_code == 200:
                    messages.success(request, f"Removal request was successful.")
                else:
                    messages.error(request, f"Error occurred with removal request")
            else:
                r = session.get("https://dig-aboprod.noncd.db.de/aboticket", params=abo_data, headers={
                    "X-User-Agent": "com.deutschebahn.abo.navigatorV2.modul",
                    "X-Api-Version": "10",
                    "X-Unique-ID": str(uuid.uuid4()),
                    "User-Agent": "Zuegli (q@magicalcodewit.ch)"
                })
                if r.status_code == 404:
                    messages.add_message(request, messages.ERROR, "Subscription not found")
                elif r.status_code == 401:
                    already_present = True
                elif not r.ok:
                    messages.add_message(request, messages.ERROR, "Unknown error")
                else:
                    if not request.user.last_name:
                        request.user.last_name = form.cleaned_data["surname"]
                        request.user.save()

                    data = r.json()
                    device_token = data["deviceToken"]
                    refresh_at = datetime.datetime.fromisoformat(data["refreshDatum"])
                    abo, _ = models.DBSubscription.objects.update_or_create(device_token=device_token, defaults={
                        "refresh_at": refresh_at,
                        "info": data["ticketHuelle"],
                        "account": request.user.account,
                    })
                    db_abo.update_abo_tickets.apply_async(args=(abo.pk,), queue="celery")
                    return redirect("db_abo")
    else:
        form = forms.DBAboForm(initial=initial)

    return render(request, "main/account/db_abo_new.html", {
        "form": form,
        "already_present": already_present,
    })


@login_required
def delete_abo(request, abo_id):
    subscription = get_object_or_404(models.DBSubscription, pk=abo_id)
    if subscription.account != request.user.account:
        return redirect("db_abo")

    if request.method == "POST" and request.POST.get("action") == "remove":
        r = session.post("https://dig-aboprod.noncd.db.de/aboticket/logout", json={
            "deviceToken": subscription.device_token,
        }, headers={
            "X-User-Agent": "com.deutschebahn.abo.navigatorV2.modul",
            "X-Api-Version": "10",
            "X-Unique-ID": str(uuid.uuid4()),
            "User-Agent": "Zuegli (q@magicalcodewit.ch)"
        })
        if r.status_code == 200:
            messages.success(request, "Removal request was successful.")
            subscription.delete()
        else:
            messages.error(request, "Error occurred with removal request")
        return redirect("db_abo")

    return render(request, "main/account/db_abo_delete.html", {})
