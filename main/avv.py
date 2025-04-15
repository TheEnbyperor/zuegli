import datetime
import niquests
import niquests.exceptions
import niquests.adapters
import logging
import urllib3.util
from django.utils import timezone
from . import models, ticket, views

logger = logging.getLogger(__name__)
retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)


def update_all():
    adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
    session = niquests.Session()
    session.mount("https://", adapter)


    for account in models.Account.objects.all():
        update_avv_tickets(account)


def update_avv_tickets(account: "models.Account"):
    client_token = views.avv.get_avv_client_token()

    if not account.is_avv_authenticated():
        return

    avv_token = views.avv.get_avv_token(account)
    if not avv_token:
        logger.error(f"Failed to get access token for account {account}")
        return

    now = timezone.now()

    r = niquests.post("https://zvp-hgs.avv.de/cxf/mobile_api/entitlement_rest/v2/entitlements", headers={
        "Authorization": f"Bearer {avv_token}",
        "ClientToken": client_token,
        "deviceId": account.avv_device_id,
        "language": "de",
        "User-Agent": "Zügli (q@magicalcodewit.ch)"
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
            "User-Agent": "Zügli (q@magicalcodewit.ch)"
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
                ticket_obj = ticket.update_from_subscription_barcode(barcode_data, account=account)
                ticket_obj.avv_account = account
                ticket_obj.save()
                logger.info(f"Updated ticket {eid} for account {account}")
            except ticket.TicketError as e:
                logger.error("Error decoding barcode ticket: %s", e)
                continue
