import base64
import niquests
import logging
import bs4
import secrets

from . import models, aztec, ticket, apn, views

logger = logging.getLogger(__name__)


def update_all():
    for account in models.Account.objects.all():
        if not account.is_db_authenticated:
            continue

        db_token = views.db.get_db_token(account)
        if not db_token:
            continue

        r = niquests.get(f"https://app.vendo.noncd.db.de/mob/reisenuebersicht", params={
            "kundenprofilId": account.db_account_id,
        }, headers={
            "Authorization": f"Bearer {db_token}",
            "Accept": "application/x.db.vendo.mob.reisenuebersicht.v5+json",
            "X-Correlation-ID": secrets.token_hex(16),
            "User-Agent": "VDV PKPass q@magicalcodewit.ch",
        })
        if r.status_code != 200:
            continue

        data = r.json()
        for auftrag in data["auftragsIndizes"]:
            auftragsnummer = auftrag["auftragsnummer"]
            for kundenwunsch_id in auftrag["kundenwunschIds"]:
                r = niquests.get(f"https://app.vendo.noncd.db.de/mob/auftrag/{auftragsnummer}/kundenwunsch/{kundenwunsch_id}", headers={
                    "Authorization": f"Bearer {db_token}",
                    "Accept": "application/x.db.vendo.mob.auftraege.v7+json",
                    "X-Correlation-ID": secrets.token_hex(16),
                    "User-Agent": "VDV PKPass q@magicalcodewit.ch",
                })
                print(r.text)
