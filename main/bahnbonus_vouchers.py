import niquests
import niquests.exceptions
import niquests.adapters
import logging
import urllib3.util

from . import models, ticket, views

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
        if not account.is_bahnbonus_authenticated():
            continue

        bb_token = views.db.get_bahnbonus_token(account)
        if not bb_token:
            logger.error(f"Failed to get BahnBonus access token for account {account}")
            continue

        try:
            r = session.get("https://apis.deutschebahn.com/db/apis/bahnbonus/benefits-service/v1/digital-vouchers", headers={
                "Authorization": f"Bearer {bb_token}",
                "DB-Client-ID": "b4ceb052260d1df18955c9769f2f6ee1",
                "DB-Client-Secret": "af42968e4445cf550ad06f8b114f0cda",
                "User-Agent": "VDV PKPass q@magicalcodewit.ch",
            })
            if not r.ok:
                logger.error(f"Failed to get vouchers for account {account} - {r.text}")
                continue
        except niquests.exceptions.RequestException as e:
            logger.error(f"Failed to get vouchers for account {account}: {e}")
            continue

        vouchers = r.json()
        for voucher in vouchers:
            for instance in voucher["vouchers"]:
                aztec_code = next(filter(lambda c: c["type"] == "aztecCode", instance["components"]), None)
                if not aztec_code:
                    continue

                aztec_code = aztec_code["aztecCode"]["payload"].encode("utf-8")

                try:
                    ticket_obj = ticket.update_from_subscription_barcode(aztec_code, account=account)
                    ticket_obj.save()
                except ticket.TicketError as e:
                    logger.error("Error decoding barcode: %s", e)
                    continue
