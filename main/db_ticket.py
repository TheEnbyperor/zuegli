import base64
import niquests.exceptions
import bs4
import secrets
from celery import shared_task
from celery.utils.log import get_task_logger
from . import models, aztec, ticket, oauth, apn, session

logger = get_task_logger(__name__)


def update_from_img_elm(barcode_elm, account):
    barcode_url = barcode_elm.attrs["src"]
    if not barcode_url.startswith("data:"):
        logger.error("Barcode image not a data URL")
        return None
    media_type, data = barcode_url[5:].split(";", 1)
    encoding, data = data.split(",", 1)
    if not media_type.startswith("image/"):
        logger.error("Unsupported media type '%s'", media_type)
        return None
    if encoding != "base64":
        logger.error("Unsupported encoding type '%s' in barcode image", encoding)
        return None
    barcode_img_data = base64.urlsafe_b64decode(data)
    try:
        barcode_data = aztec.decode(barcode_img_data)
    except aztec.AztecError as e:
        logger.error("Error decoding barcode image: %s", e)
        return None

    try:
        ticket_obj, _ = ticket.update_from_barcode(barcode_data, account=account)
        return ticket_obj
    except ticket.TicketError as e:
        logger.error("Error decoding barcode ticket: %s", e)
        return None


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_all():
    for account in models.Account.objects.all():
        if not account.is_db_authenticated():
            continue

        if not oauth.get_token(account, "db"):
            continue

        update_account.apply_async((account.pk,), expires=14400)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=25, default_retry_delay=3,
    ignore_result=True
)
def update_account(account_id):
    account = models.Account.objects.get(pk=account_id)
    db_token = oauth.get_token(account, "db")
    if not db_token:
        logger.error(f"Failed to get access token for account {account}")
        return

    account_oauth = models.AccountOAuth.objects.get(account=account, provider="db")
    account_id = account_oauth.extra_data["account_id"]

    try:
        r = session.post(f"https://app.vendo.noncd.db.de/mob/kundenkonten/{account_id}", headers={
            "Authorization": f"Bearer {db_token}",
            "Accept": "application/x.db.vendo.mob.kundenkonto.v7+json",
            "X-Correlation-ID": secrets.token_hex(16),
            "User-Agent": "Zuegli (q@magicalcodewit.ch)",
        })
        if not r.ok:
            logger.error(f"Failed to get profiles for account {account_id} - {r.text}")
            return
    except niquests.exceptions.RequestException as e:
        logger.error(f"Failed to get profiles for account {account_id}: {e}")
        return

    account_data = r.json()
    for profile in account_data["kundenprofile"]:
        profile_id = profile["id"]
        db_token = oauth.get_token(account, "db")
        try:
            r = session.get("https://app.vendo.noncd.db.de/mob/reisenuebersicht", params={
                "kundenprofilId": profile_id,
            }, headers={
                "Authorization": f"Bearer {db_token}",
                "Accept": "application/x.db.vendo.mob.reisenuebersicht.v5+json",
                "X-Correlation-ID": secrets.token_hex(16),
                "User-Agent": "Zuegli (q@magicalcodewit.ch)",
            }, timeout=10)
            if not r.ok:
                logger.error(f"Failed to get bookings for profile {profile_id} - {r.text}")
                continue
        except niquests.exceptions.RequestException as e:
            logger.error(f"Failed to get bookings for profile {profile_id}: {e}")
            continue

        profile_data = r.json()
        for auftrag in profile_data["auftragsIndizes"]:
            auftragsnummer = auftrag["auftragsnummer"]
            for kundenwunsch_id in auftrag["kundenwunschIds"]:
                db_token = oauth.get_token(account, "db")
                try:
                    r = session.get(f"https://app.vendo.noncd.db.de/mob/auftrag/{auftragsnummer}/kundenwunsch/{kundenwunsch_id}", headers={
                        "Authorization": f"Bearer {db_token}",
                        "Accept": "application/x.db.vendo.mob.auftraege.v9+json",
                        "X-Correlation-ID": secrets.token_hex(16),
                        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
                    }, timeout=10)
                    if not r.ok:
                        logger.error(f"Failed to get ticket for booking {auftragsnummer} - {kundenwunsch_id}: {r.text}")
                        continue
                except niquests.exceptions.RequestException as e:
                    logger.error(f"Failed to get ticket for booking {auftragsnummer} - {kundenwunsch_id}: {e}")
                    continue

                ticket_data = r.json()
                if not ticket_data.get("ticket"):
                    continue

                ticket_data = base64.urlsafe_b64decode(ticket_data["reise"]["reiseInfos"]["ticket"]["ticket"] + '==')
                ticket_layout = bs4.BeautifulSoup(ticket_data, 'html.parser')
                barcode_elm = ticket_layout.find("img", attrs={
                    "id": "ticketbarcode"
                }, recursive=True)
                if not barcode_elm:
                    logger.error(f"Could not find barcode element - account {account}")
                    continue

                logger.info(f"Found barcode element - ticket ID {auftragsnummer}")

                update_from_img_elm(barcode_elm, account)

    for t in account_oauth.tickets.all():
        apn.notify_ticket_if_renewed(t)
