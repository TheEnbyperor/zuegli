import niquests
import logging
import json
import base64
from . import models, eos, ticket, apn, aztec

logger = logging.getLogger(__name__)


def update_all():
    for account in models.Account.objects.filter(saarvv_device_id__isnull=False):
        update_saarvv_tickets(account)

        for t in account.saarvv_tickets.all():
            apn.notify_ticket_if_renewed(t)


def update_saarvv_tickets(account: "models.Account"):
    if not account.saarvv_token or not account.saarvv_device_id:
        return

    r = niquests.post("https://saarvv.tickeos.de/index.php/mobileService/sync", json={}, hooks={
        "pre_request": [lambda req: eos.sign_request(req, account.saarvv_device_id, "saarvv")],
    }, headers={
        "Authorization": account.saarvv_token
    })
    if not r.ok:
        logger.error(f"Failed to update SaarVV {account.saarvv_device_id}: {r.text}")
    data = r.json()

    r = niquests.post("https://saarvv.tickeos.de/index.php/mobileService/ticket", json={
        "details": True,
        "tickets": data["tickets"],
        "provide_aztec_content": False,
        "parameters": False,
    }, hooks={
        "pre_request": [lambda req: eos.sign_request(req, account.saarvv_device_id, "saarvv")],
    }, headers={
        "Authorization": account.saarvv_token
    })
    if not r.ok:
        logger.error(f"Failed to update SaarVV {account.saarvv_device_id}: {r.text}")
    data = r.json()
    for t in data["tickets"].values():
        template = json.loads(t["template"])
        barcode_img = base64.b64decode(template["content"]["images"]["aztec_barcode"])
        barcode_data = aztec.decode(barcode_img)

        try:
            ticket_obj = ticket.update_from_subscription_barcode(barcode_data, account=account)
            ticket_obj.saarvv_account = account
            ticket_obj.save()
        except ticket.TicketError as e:
            logger.error("Error decoding barcode ticket: %s", e)
            continue

    logger.info(f"Successfully updated SaarVV {account.saarvv_device_id}")
