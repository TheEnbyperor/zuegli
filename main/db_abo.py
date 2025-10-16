import base64
import json
import niquests.adapters
import datetime
import bs4
import urllib3.util
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from . import models, aztec, ticket, apn

logger = get_task_logger(__name__)
retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
session = niquests.Session()
session.mount("https://", adapter)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_all():
    now = timezone.now()
    for abo in models.DBSubscription.objects.all():
        if abo.refresh_at <= now:
            update_abo_tickets.delay(abo.pk)
        else:
            logger.info(f"Not updating DB subscription {abo.device_token} - not due for refresh")


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=3, default_retry_delay=3,
    ignore_result=True
)
def update_abo_tickets(abo_id):
    try:
        abo = models.DBSubscription.objects.get(pk=abo_id)
    except models.DBSubscription.DoesNotExist:
        return
    r = session.post("https://dig-aboprod.noncd.db.de/aboticket/refreshmultiple", json={
        "aboTicketCheckRequestList": [{
            "deviceToken": abo.device_token,
        }]
    }, headers={
        "X-User-Agent": "com.deutschebahn.abo.navigatorV2.modul",
        "X-Api-Version": "9",
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })

    if r.status_code == 404:
        abo.delete()
        return

    r.raise_for_status()
    data = r.json()

    if len(data) == 0:
        abo.delete()
        return

    tickets = data[0]
    abo.refresh_at = datetime.datetime.fromisoformat(tickets['refreshDatum'])
    abo.info = tickets["ticketHuelle"]
    abo.save()

    for t in tickets["tickets"]:
        ticket_data = base64.urlsafe_b64decode(t["payload"] + '==')
        ticket_data = json.loads(ticket_data.decode('utf-8'))
        if "barcode" in ticket_data and ticket_data["barcode"]:
            barcode_url = ticket_data["barcode"]
        else:
            ticket_layout = bs4.BeautifulSoup(ticket_data["ticketLayoutTemplate"], 'html.parser')
            barcode_elm = ticket_layout.find("nativeimg", attrs={
                "id": "ticketbarcode"
            }, recursive=True)
            if not barcode_elm:
                barcode_elm = ticket_layout.find("img", attrs={
                    "id": "ticketbarcode"
                }, recursive=True)
            if not barcode_elm:
                logger.error("Could not find barcode element")
                continue
            barcode_url = barcode_elm.attrs["src"]

        if not barcode_url.startswith("data:"):
            logger.error("Barcode image not a data URL")
            continue
        media_type, data = barcode_url[5:].split(";", 1)
        encoding, data = data.split(",", 1)
        if not media_type.startswith("image/"):
            logger.error("Unsupported media type '%s'", media_type)
            continue
        if encoding != "base64":
            logger.error("Unsupported encoding type '%s' in barcode image", encoding)
            continue
        barcode_img_data = base64.urlsafe_b64decode(data)
        try:
            barcode_data = aztec.decode(barcode_img_data)
        except aztec.AztecError as e:
            logger.error("Error decoding barcode image: %s", e)
            continue

        try:
            ticket_obj, _ = ticket.update_from_barcode(barcode_data, account=abo.account)
            ticket_obj.db_subscription = abo
            ticket_obj.save()
        except ticket.TicketError as e:
            logger.error("Error decoding barcode ticket: %s", e)
            continue

    logger.info(f"Successfully updated DB subscription {abo.device_token}")

    for t in abo.tickets.all():
        apn.notify_ticket_if_renewed(t)
