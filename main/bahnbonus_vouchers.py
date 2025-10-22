import niquests
import niquests.exceptions
from celery import shared_task
from celery.utils.log import get_task_logger
from . import models, ticket, oauth, session

logger = get_task_logger(__name__)

@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_all():
    for account in models.Account.objects.all():
        if not account.is_bahnbonus_authenticated():
            continue

        update_account.delay(account.pk)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=25, default_retry_delay=3,
    ignore_result=True
)
def update_account(account_id):
    account = models.Account.objects.get(pk=account_id)
    bb_token = oauth.get_token(account, "bahnbonus")
    if not bb_token:
        logger.error(f"Failed to get BahnBonus access token for account {account}")
        return

    try:
        r = session.get("https://apis.deutschebahn.com/db/apis/bahnbonus/benefits-service/v1/digital-vouchers", headers={
            "Authorization": f"Bearer {bb_token}",
            "DB-Client-ID": "b4ceb052260d1df18955c9769f2f6ee1",
            "DB-API-Key": "af42968e4445cf550ad06f8b114f0cda",
            "User-Agent": "Zuegli (q@magicalcodewit.ch)",
        })
        if not r.ok:
            logger.error(f"Failed to get vouchers for account {account} - {r.text}")
            return
    except niquests.exceptions.RequestException as e:
        logger.error(f"Failed to get vouchers for account {account}: {e}")
        return

    vouchers = r.json()
    for voucher in vouchers:
        for instance in voucher["vouchers"]:
            aztec_code = next(filter(lambda c: c["type"] == "aztecCode", instance["components"]), None)
            if not aztec_code:
                continue

            aztec_code = aztec_code["aztecCode"]["payload"].encode("utf-8")

            try:
                ticket.update_from_barcode(aztec_code, account=account)
            except ticket.TicketError as e:
                logger.error("Error decoding barcode: %s", e)
                continue
