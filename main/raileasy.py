import typing
import niquests
import niquests.adapters
import datetime
import logging
import urllib3.util
import pymupdf
from django.utils import timezone
from django.conf import settings
from . import models, apn, aztec, ticket

logger = logging.getLogger(__name__)
retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)

def get_token(account: "models.Account") -> typing.Optional[str]:
    now = timezone.now()
    oauth = models.AccountOAuth.objects.filter(account=account, provider="raileasy").first()
    if not oauth:
        return None

    if oauth.token and oauth.token_expires_at and oauth.token_expires_at > now - datetime.timedelta(minutes=3):
        return oauth.token
    elif oauth.refresh_token:
        r = niquests.post("https://securetoken.googleapis.com/v1/token", params={
                "key": settings.RAILEASY_API_KEY,
            }, data={
                "grant_type": "refresh_token",
                "refresh_token": oauth.refresh_token,
            }, headers={
                "User-Agent": "Zuegli (q@magicalcodewit.ch)"
            })
        if not r.ok:
            return None

        data = r.json()
        oauth.token = data["id_token"]
        oauth.token_expires_at = now + datetime.timedelta(seconds=int(data["expires_in"]))
        oauth.refresh_token = data.get("refresh_token", None)
        oauth.refresh_token_expires_at = None
        oauth.save()
        return oauth.token

    return None


def update_all():
    for oauth in models.AccountOAuth.objects.filter(provider="raileasy", token__isnull=False):
        update_tickets(oauth.account)

        for t in oauth.tickets.all():
            apn.notify_ticket_if_renewed(t)


def update_tickets(account: "models.Account"):
    adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
    session = niquests.Session()
    session.mount("https://", adapter)

    logger.info(f"Updating Raileasy {account}")

    token = get_token(account)
    if not token:
        return

    oauth_token = models.AccountOAuth.objects.get(account=account, provider="raileasy")

    r = session.get("https://raileasy.co.uk/api/GetJourneyList", params={
        "includeOld": "true",
        "pageSize": "1000"
    }, headers={
        "firebaseToken": token,
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    for journey in r.json()["journeys"]:
        r = session.post("https://raileasy.co.uk/api/GetIndividualJourney", json={
            "journeyId": journey["journeyId"],
            "purchaseId": journey["purchaseId"],
        }, headers={
            "firebaseToken": token,
            "User-Agent": "Zuegli (q@magicalcodewit.ch)"
        })
        for t in r.json()["tickets"]:
            for d in t["passengerDetails"]:
                pdf_r = session.get(d["pdfUrl"])
                if not pdf_r.ok:
                    logger.warning(f"Could not fetch {d['pdfUrl']}")
                else:
                    try:
                        pdf = pymupdf.open(stream=pdf_r.content, filetype="application/pdf")
                    except RuntimeError as e:
                        logger.error(f"Error opening PDF: {e}")
                    else:
                        for page in pdf:
                            img_bytes = page.get_pixmap(dpi=300).tobytes()
                            try:
                                barcode_data = aztec.decode(img_bytes)
                            except aztec.AztecError:
                                continue

                            try:
                                ticket_obj = ticket.update_from_subscription_barcode(barcode_data, account=account)
                                ticket_obj.oauth_account = oauth_token
                                ticket_obj.save()
                            except ticket.TicketError as e:
                                logger.error("Error decoding barcode ticket: %s", e)
                                continue
