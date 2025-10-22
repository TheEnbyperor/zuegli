import io
import zipfile
import json
from django.utils import timezone
from django.conf import settings
import datetime
import niquests
import jwt
from celery import shared_task
from celery.utils.log import get_task_logger
from . import models, ticket, session

logger = get_task_logger(__name__)


def get_auth_token(account: "models.Account"):
    oauth = models.AccountOAuth.objects.get(account=account, provider="hvv")
    now = timezone.now()
    if not oauth:
        return None

    if oauth.token and oauth.token_expires_at and oauth.token_expires_at - datetime.timedelta(minutes=3) > now:
        return oauth.token
    elif oauth.refresh_token:
        r = session.get("https://api.hochbahn.cloud/auth/token/refresh", headers={
            "x-beam-refresh-token": f"Bearer {settings.HVV_APPLICATION_KEY}/{oauth.refresh_token}",
            "User-Agent": "Zuegli (q@magicalcodewit.ch)",
        })
        if r.status_code != 200:
            return None

        access_token = r.headers["authorization"][len("Bearer "):]
        refresh_token = r.headers["x-beam-refresh-token"]

        auth_data = jwt.decode(access_token, options={"verify_signature": False})
        expiry = datetime.datetime.fromtimestamp(auth_data["exp"])

        oauth.token = access_token
        oauth.token_expires_at = expiry
        oauth.refresh_token = refresh_token
        oauth.save()

        return access_token
    else:
        return None


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_all():
    for account in models.Account.objects.all():
        if not account.is_hvv_authenticated():
            continue

        update_hvv_tickets.delay(account.pk)

@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=25, default_retry_delay=3,
    ignore_result=True
)
def update_hvv_tickets(account_id):
    account = models.Account.objects.get(id=account_id)
    token = get_auth_token(account)
    if not token:
        return

    r = session.get("https://api.hochbahn.cloud/orders", params={
        "pageSize": "0",
    }, headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    })
    if not r.ok:
        logger.error(f"Failed to get HVV orders for {account}: {r.text}")
        return

    data = r.json()

    for order in data["content"]:
        if "ticketPublicUUID" not in order:
            continue
        token = get_auth_token(account)
        r = session.get(f"https://api.hochbahn.cloud/ride/wallet/tickets/{order['ticketPublicUUID']}/pkpass", headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Zuegli (q@magicalcodewit.ch)",
        })
        if not r.ok:
            continue
        f = zipfile.ZipFile(io.BytesIO(r.content))
        pass_json = json.load(f.open("pass.json"))
        ticket_barcode = pass_json["barcodes"][0]["message"].encode("ISO-8859-1")
        try:
            ticket_obj, _ = ticket.update_from_barcode(ticket_barcode, account=account)
            ticket_obj.oauth_account = models.AccountOAuth.objects.get(account=account, provider="hvv")
            ticket_obj.save()
            logger.info(f"Updated ticket {order['ticketPublicUUID']} for account {account}")
        except ticket.TicketError as e:
            logger.error("Error decoding barcode ticket: %s", e)

    token = get_auth_token(account)
    r = session.get("https://api.hochbahn.cloud/subscriptions/orders", headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    })
    if not r.ok:
        logger.error(f"Failed to get HVV subscriptions for {account}: {r.text}")
        return

    data = r.json()

    for sub in data["content"]:
        token = get_auth_token(account)
        r = session.get(f"https://api.hochbahn.cloud/ride/wallet/subscriptions/{sub['subscriptionID']}/pkpass", headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Zuegli (q@magicalcodewit.ch)",
        })
        if not r.ok:
            continue
        f = zipfile.ZipFile(io.BytesIO(r.content))
        pass_json = json.load(f.open("pass.json"))
        ticket_barcode = pass_json["barcodes"][0]["message"].encode("ISO-8859-1")
        try:
            ticket_obj, _ = ticket.update_from_barcode(ticket_barcode, account=account)
            ticket_obj.oauth_account = models.AccountOAuth.objects.get(account=account, provider="hvv")
            ticket_obj.save()
            logger.info(f"Updated subscription {sub['subscriptionID']} for account {account}")
        except ticket.TicketError as e:
            logger.error("Error decoding barcode ticket: %s", e)
