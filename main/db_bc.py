import base64
import niquests
import niquests.exceptions
import niquests.adapters
import logging
import bs4
import secrets
import urllib3.util

from . import models, views, db_ticket

logger = logging.getLogger(__name__)
retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[403, 429, 500, 502, 503, 504],
)


def update_all():
    adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
    session = niquests.Session()
    session.mount("https://", adapter)

    for account in models.Account.objects.all():
        if not account.is_db_authenticated:
            continue

        db_token = views.db.get_db_token(account)
        if not db_token:
            continue

        try:
            r = niquests.get(f"https://app.vendo.noncd.db.de/mob/emobilebahncards", headers={
                "Authorization": f"Bearer {db_token}",
                "Accept": "application/x.db.vendo.mob.emobilebahncards.v2+json",
                "X-Correlation-ID": secrets.token_hex(16),
                "User-Agent": "VDV PKPass q@magicalcodewit.ch",
                "Call-Trigger": "manual"
            })
            if not r.ok:
                logger.error(f"Failed to get BahnCards for account {account} - {r.text}")
                continue
        except niquests.exceptions.RequestException as e:
            logger.error(f"Failed to get BahnCards for account {account} - {e}")
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

            db_ticket.update_from_img_elm(barcode_elm, account)
