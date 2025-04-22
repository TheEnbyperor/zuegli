import base64
import niquests
import niquests.exceptions
import niquests.adapters
import logging
import urllib3.util
from . import models, ticket, views, aztec

logger = logging.getLogger(__name__)
retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)

PROVIDERS = {
    "vestische": {
        "orders": "https://ticketshop.vestische.de/TicketShop/Shop/ListOrdersV2",
        "barcode": "https://ticketshop.vestische.de/TicketShop/Shop/QRCode"
    }
}

def update_all():
    adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
    session = niquests.Session()
    session.mount("https://", adapter)

    for account in models.Account.objects.all():
        update_vrr_tickets(session, account)


def update_vrr_tickets(session, account: "models.Account"):
    for provider_id, provider in PROVIDERS.items():
        oauth = account.oauth.filter(provider=provider_id).first()
        if not oauth:
            continue
        if not oauth.is_authenticated():
            continue

        token = views.vrr.get_token(account, provider_id)
        if not token:
            logger.error(f"Failed to get access token for account {account}")
            return

        r = session.post(provider["orders"], headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Zuegli (q@magicalcodewit.ch)"
        }, json={
          "ListOrdersTimeFilterMask": 5,
          "ListOrdersTicketFilterMask": 15
        })
        if not r.ok:
            logger.error(f"Failed to get tickets for account {account}")
            return
        data = r.json()

        for order in data["Orders"]:
            for t in order["Tickets"]:
                r = session.post(provider["barcode"], headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Zuegli (q@magicalcodewit.ch)"
                }, json={
                    "Id": t["ID"],
                })
                if not r.ok:
                    logger.error(f"Failed to get barcode for ticket {t['ID']} on account {account}")
                    return

                barcode = r.json()
                if barcode["QrCode"]:
                    try:
                        barcode_img_data = base64.b64decode(barcode["QrCode"])
                    except ValueError:
                        logger.error(f"Failed to decode barcode contents for ticket {t['ID']} on account{account}")
                        continue

                    try:
                        barcode_data = aztec.decode(barcode_img_data)
                    except aztec.AztecError as e:
                        logger.error("Error decoding barcode image: %s", e)
                        continue

                    try:
                        ticket_obj = ticket.update_from_subscription_barcode(barcode_data, account=account)
                        ticket_obj.oauth_account = oauth
                        ticket_obj.save()
                        logger.info(f"Updated ticket {t['ID']} for account {account}")
                    except ticket.TicketError as e:
                        logger.error(f"Error decoding barcode ticket: {e}")
