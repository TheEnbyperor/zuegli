import base64
import niquests
import logging
import bs4
import secrets

from . import models, aztec, ticket, apn, views

logger = logging.getLogger(__name__)


def update_from_img_elm(barcode_elm, account):
    barcode_url = barcode_elm.attrs["src"]
    if not barcode_url.startswith("data:"):
        logger.error("Barcode image not a data URL")
        return
    media_type, data = barcode_url[5:].split(";", 1)
    encoding, data = data.split(",", 1)
    if not media_type.startswith("image/"):
        logger.error("Unsupported media type '%s'", media_type)
        return
    if encoding != "base64":
        logger.error("Unsupported encoding type '%s' in barcode image", encoding)
        return
    barcode_img_data = base64.urlsafe_b64decode(data)
    try:
        barcode_data = aztec.decode(barcode_img_data)
    except aztec.AztecError as e:
        logger.error("Error decoding barcode image: %s", e)
        return

    try:
        ticket_obj = ticket.update_from_subscription_barcode(barcode_data, account=account)
        ticket_obj.save()
        apn.notify_ticket_if_renewed(ticket_obj)
    except ticket.TicketError as e:
        logger.error("Error decoding barcode ticket: %s", e)
        return


def update_all():
    for account in models.Account.objects.all():
        if not account.is_db_authenticated:
            continue

        db_token = views.db.get_db_token(account)
        if not db_token:
            continue

        r = niquests.post(f"https://app.vendo.noncd.db.de/mob/kundenkonten/{account.db_account_id}", headers={
            "Authorization": f"Bearer {db_token}",
            "Accept": "application/x.db.vendo.mob.kundenkonto.v6+json",
            "X-Correlation-ID": secrets.token_hex(16),
            "User-Agent": "VDV PKPass q@magicalcodewit.ch",
        })
        if r.status_code != 200:
            logger.error(f"Failed to get profiles for account {account.db_account_id} - {r.text}")
            continue

        account_data = r.json()
        for profile in account_data["kundenprofile"]:
            profile_id = profile["id"]
            r = niquests.get("https://app.vendo.noncd.db.de/mob/reisenuebersicht", params={
                "kundenprofilId": profile_id,
            }, headers={
                "Authorization": f"Bearer {db_token}",
                "Accept": "application/x.db.vendo.mob.reisenuebersicht.v5+json",
                "X-Correlation-ID": secrets.token_hex(16),
                "User-Agent": "VDV PKPass q@magicalcodewit.ch",
            })
            if r.status_code != 200:
                logger.error(f"Failed to get bookings for profile {profile_id} - {r.text}")
                continue

            profile_data = r.json()
            for auftrag in profile_data["auftragsIndizes"]:
                auftragsnummer = auftrag["auftragsnummer"]
                for kundenwunsch_id in auftrag["kundenwunschIds"]:
                    r = niquests.get(f"https://app.vendo.noncd.db.de/mob/auftrag/{auftragsnummer}/kundenwunsch/{kundenwunsch_id}", headers={
                        "Authorization": f"Bearer {db_token}",
                        "Accept": "application/x.db.vendo.mob.auftraege.v7+json",
                        "X-Correlation-ID": secrets.token_hex(16),
                        "User-Agent": "VDV PKPass q@magicalcodewit.ch",
                    })

                    ticket_data = r.json()
                    if not ticket_data.get("ticket"):
                        continue

                    ticket_data = base64.urlsafe_b64decode(ticket_data["ticket"]["ticket"] + '==')
                    ticket_layout = bs4.BeautifulSoup(ticket_data, 'html.parser')
                    barcode_elm = ticket_layout.find("img", attrs={
                        "id": "ticketbarcode"
                    }, recursive=True)
                    if barcode_elm:
                        logger.error("No barcode element present")
                        continue

                    if not barcode_elm:
                        logger.error("Could not find barcode element")
                        continue

                    update_from_img_elm(barcode_elm, account)