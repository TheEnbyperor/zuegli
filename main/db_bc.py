import base64
import niquests
import logging
import bs4
import secrets

from . import models, aztec, ticket, apn, views

logger = logging.getLogger(__name__)


def update_all():
    for account in models.Account.objects.all():
        if not account.is_db_authenticated:
            continue

        db_token = views.db.get_db_token(account)
        if not db_token:
            continue

        r = niquests.get(f"https://app.vendo.noncd.db.de/mob/emobilebahncards", headers={
            "Authorization": f"Bearer {db_token}",
            "Accept": "application/x.db.vendo.mob.emobilebahncards.v2+json",
            "X-Correlation-ID": secrets.token_hex(16),
            "User-Agent": "VDV PKPass q@magicalcodewit.ch",
            "Call-Trigger": "manual"
        })
        if r.status_code != 200:
            continue

        data = r.json()
        for bc in data:
            ticket_data = base64.urlsafe_b64decode(bc["kontrollSicht"] + '==')
            ticket_layout = bs4.BeautifulSoup(ticket_data, 'html.parser')
            barcode_elm = ticket_layout.find("img", attrs={
                "id": "ticketbarcode"
            }, recursive=True)
            if barcode_elm:
                continue

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
                ticket_obj = ticket.update_from_subscription_barcode(barcode_data, account=account)
                ticket_obj.save()
                apn.notify_ticket_if_renewed(ticket_obj)
            except ticket.TicketError as e:
                logger.error("Error decoding barcode ticket: %s", e)
                continue
