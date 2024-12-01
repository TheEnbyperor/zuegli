import base64
import niquests
import logging
import bs4
import secrets

from . import models, views, db_ticket

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
            logger.error(f"Failed to get BahnCards for account {account} - {r.text}")
            continue

        data = r.json()
        for bc in data:
            ticket_data = base64.urlsafe_b64decode(bc["kontrollSicht"] + '==')
            ticket_layout = bs4.BeautifulSoup(ticket_data, 'html.parser')
            barcode_elm = ticket_layout.find("img", attrs={
                "id": "ticketbarcode"
            }, recursive=True)
            if not barcode_elm:
                logger.error("Could not find barcode element")
                continue

            db_ticket.update_from_img_elm(barcode_elm)
