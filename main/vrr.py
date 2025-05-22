import base64
import dataclasses
import niquests.adapters
import urllib3.util
from celery import shared_task
from celery.utils.log import get_task_logger
from . import models, ticket, oauth, aztec, apn


@dataclasses.dataclass
class Provider:
    orders: str
    barcode: str


logger = get_task_logger(__name__)
retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
session = niquests.Session()
session.mount("https://", adapter)

PROVIDERS = {
    "vestische": Provider(
        orders="https://ticketshop.vestische.de/TicketShop/Shop/ListOrdersV2",
        barcode="https://ticketshop.vestische.de/TicketShop/Shop/QRCode"
    ),
    "nrway": Provider(
        orders="https://nrway.dbregiobus-nrw.de/TicketShop/Shop/ListOrdersV2",
        barcode="https://nrway.dbregiobus-nrw.de/TicketShop/Shop/QRCode"
    )
}


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_all():
    for account in models.Account.objects.all():
        for provider_id, provider in PROVIDERS.items():
            if not account.is_oauth_authenticated(provider_id):
                continue

            update_vrr_tickets.delay(account.pk. provider_id)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_vrr_tickets(account_id, provider_id):
    account = models.Account.objects.get(pk=account_id)
    provider = PROVIDERS[provider_id]

    logger.info(f"Updating {provider_id} for account {account}")

    token = oauth.get_token(account, provider_id)
    if not token:
        logger.error(f"Failed to get access token for account {account}")
        return

    account_oauth = models.AccountOAuth.objects.get(account=account, provider=provider_id)

    r = session.post(provider.orders, headers={
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
            r = session.post(provider.barcode, headers={
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
                    ticket_obj, _ = ticket.update_from_barcode(barcode_data, account=account)
                    ticket_obj.oauth_account = account
                    ticket_obj.save()
                    logger.info(f"Updated ticket {t['ID']} for account {account}")
                except ticket.TicketError as e:
                    logger.error(f"Error decoding barcode ticket: {e}")

    for t in account_oauth.tickets.all():
        apn.notify_ticket_if_renewed(t)

    logger.info(f"Updated {provider_id} for account {account}")
