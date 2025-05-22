import datetime
import niquests
import niquests.exceptions
import niquests.adapters
import urllib3.util
from django.utils import timezone
from celery import shared_task
from celery.utils.log import get_task_logger
from . import models, ticket, views, oauth, apn

logger = get_task_logger(__name__)
retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_all():
    adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
    session = niquests.Session()
    session.mount("https://", adapter)

    for account in models.Account.objects.all():
        update_avv_tickets.delay(account.pk)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_avv_tickets(account_id):
    account = models.Account.objects.get(pk=account_id)
    client_token = views.avv.get_avv_client_token()

    if not account.is_avv_authenticated():
        return

    avv_token = oauth.get_token(account, "avv")
    if not avv_token:
        logger.error(f"Failed to get access token for account {account}")
        return

    account_oauth = models.AccountOAuth.objects.get(account=account, provider="avv")
    now = timezone.now()

    r = niquests.post("https://zvp-hgs.avv.de/cxf/mobile_api/entitlement_rest/v2/entitlements", headers={
        "Authorization": f"Bearer {avv_token}",
        "ClientToken": client_token,
        "deviceId": account_oauth.device_id,
        "language": "de",
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    }, json={
        "fromDtm": (now - datetime.timedelta(days=30)).isoformat(),
        "toDtm": (now + datetime.timedelta(days=30)).isoformat(),
        "status": "ACTIVE",
        "tableSearch": {
            "offset": 0,
            "pageSize": 100,
            "sortField": "validityStart",
            "sortOrder": "ASCENDING"
        }
    })
    if not r.ok:
        logger.error(f"Failed to get tickets for account {account}")
        return
    data = r.json()

    for entitlement in data["entitlements"]:
        eid = entitlement["entitlementId"]
        r = niquests.get(f"https://zvp-hgs.avv.de/cxf/mobile_api/entitlement_rest/v2/entitlements/{eid}", headers={
            "Authorization": f"Bearer {avv_token}",
            "ClientToken": client_token,
            "deviceId": entitlement["deviceId"],
            "language": "de",
            "User-Agent": "Zuegli (q@magicalcodewit.ch)"
        })
        if not r.ok:
            logger.error(f"Failed to get ticket {eid} for account {account}")
            continue
        t = r.json()

        for e in t["entitlements"]:
            if e["discriminator"] != "staticEntitlement":
                continue

            barcode_data = bytes.fromhex(e["signedStaticEntitlementWithSecurity"])
            try:
                ticket_obj, _ = ticket.update_from_barcode(barcode_data, account=account)
                ticket_obj.oauth_account = account_oauth
                ticket_obj.save()
                logger.info(f"Updated ticket {eid} for account {account}")
            except ticket.TicketError as e:
                logger.error("Error decoding barcode ticket: %s", e)
                continue

    for t in account_oauth.tickets.all():
        apn.notify_ticket_if_renewed(t)
