import niquests
import urllib.parse
from django.conf import settings
from django.utils import timezone
from celery import shared_task
from . import models, gwallet


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def notify_device(device_id):
    try:
        device = models.AppleDevice.objects.get(pk=device_id)
    except models.AppleDevice.DoesNotExist:
        return
    r = niquests.post(f"https://api.push.apple.com/3/device/{device.push_token}", headers={
        "apns-push-type": "alert",
        "apns-priority": "10"
    }, json={
        "aps": {
            "content-available": 1
        }
    }, cert=(str(settings.PKPASS_CERTIFICATE_LOCATION), str(settings.PKPASS_KEY_LOCATION)))
    if r.status_code == 410:
        device.delete()
        return
    r.raise_for_status()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def notify_android_pass_device(device_id):
    device = models.AndroidPassDevice.objects.get(pk=device_id)
    r = niquests.post("https://walletpasses.appspot.com/api/v1/push", json={
        "passTypeIdentifier": settings.PKPASS_CONF["pass_type"],
        "pushTokens": [device.push_token],
    }, headers={
        "Authorization": settings.WALLET_PASSES_API_KEY
    })
    r.raise_for_status()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def notify_attido_device(device_id):
    device = models.AttidoDevice.objects.get(pk=device_id)
    url = urllib.parse.urljoin(device.push_service_url, "v1/pushUpdate")
    r = niquests.post(url, json={
        "passTypeID": settings.PKPASS_CONF["pass_type"],
        "pushToken": device.push_token,
    })
    r.raise_for_status()

@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def notify_ticket(ticket_id):
    ticket = models.Ticket.objects.get(id=ticket_id)
    for registration in ticket.apple_registrations.all():
        notify_device.delay(registration.device_id)
    for registration in ticket.android_pass_registrations.all():
        notify_android_pass_device.delay(registration.device_id)
    for registration in ticket.attido_registrations.all():
        notify_attido_device.delay(registration.device_id)



def notify_ticket_if_renewed(ticket):
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
            notify_ticket.delay(ticket.pk)
            gwallet.sync_ticket.delay(ticket.pk)