import niquests
from django.conf import settings
from django.utils import timezone
from . import models, gwallet

def notify_device(device: "models.AppleDevice"):
    r = niquests.post(f"https://api.push.apple.com/3/device/{device.push_token}", headers={
        "apns-push-type": "alert",
        "apns-priority": "10"
    }, json={
        "aps": {
            "content-available": 1
        }
    }, cert=(str(settings.PKPASS_CERTIFICATE_LOCATION), str(settings.PKPASS_KEY_LOCATION)))
    r.raise_for_status()


def notify_android_pass_device(device: "models.AndroidPassDevice"):
    r = niquests.post("https://walletpasses.appspot.com/api/v1/push", json={
        "passTypeIdentifier": settings.PKPASS_CONF["pass_type"],
        "pushTokens": [device.push_token],
    }, headers={
        "Authorization": settings.WALLET_PASSES_API_KEY
    })
    print(r.text)
    r.raise_for_status()


def notify_attido_device(device: "models.AttidoDevice"):
    r = niquests.post(f"{device.push_service_url}/v1/pushUpdate", json={
        "passTypeID": settings.PKPASS_CONF["pass_type"],
        "pushToken": device.push_token,
    })
    r.raise_for_status()


def notify_ticket(ticket: "models.Ticket"):
    for registration in ticket.apple_registrations.all():
        notify_device(registration.device)
    for registration in ticket.android_pass_registrations.all():
        notify_android_pass_device(registration.device)
    for registration in ticket.attido_registrations.all():
        notify_attido_device(registration.device)


def notify_ticket_if_renewed(ticket: "models.Ticket"):
    now = timezone.now()
    current_ticket_valid_from = None
    uic_tickets = ticket.uic_instances.filter(validity_start__lt=now).order_by("-validity_end")
    if uic_tickets.count() != 0:
        current_ticket_valid_from = uic_tickets[0].validity_start
    else:
        vdv_tickets = ticket.vdv_instances.filter(validity_start__lt=now).order_by("-validity_end")
        if vdv_tickets.count() != 0:
            current_ticket_valid_from = vdv_tickets[0].validity_start

    if current_ticket_valid_from:
        if current_ticket_valid_from > ticket.last_updated:
            ticket.last_updated = now
            ticket.save()
            notify_ticket(ticket)
            gwallet.sync_ticket(ticket)