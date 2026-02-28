import time

import niquests
import secrets
import hashlib
import json
import datetime
import logging
import hmac
import base64
import bs4
import urllib.parse
from Crypto.Cipher import AES
from django.core.files.storage import storages
from . import models, aztec, ticket, apn, session


logger = logging.getLogger(__name__)

EOS_INSTANCES = {}


def get_device_id():
    device_id = secrets.token_hex(16)
    return hashlib.sha1(device_id.encode()).hexdigest()


def get_eos_instance(eos_type: str):
    global EOS_INSTANCES

    if EOS_INSTANCES.get(eos_type):
        return EOS_INSTANCES[eos_type]

    with storages["staticfiles"].open(f"eos/{eos_type}.lcs", "rb") as f:
        encrypted_license = f.read()

    with storages["staticfiles"].open(f"eos/{eos_type}.json", "rb") as f:
        license_info = json.load(f)

    encryption_key = hashlib.sha512(
        f"{license_info['flavour']}{license_info['commit_hash']}".encode("utf-8")
    ).hexdigest()[:16].encode("utf-8")
    cipher = AES.new(encryption_key, AES.MODE_CBC, iv=bytes(16))
    decrypted_license = cipher.decrypt(encrypted_license)
    eos_license = json.loads(decrypted_license)
    eos_instance = eos_license["instances"][0]
    EOS_INSTANCES[eos_type] = eos_instance, license_info
    return eos_instance, license_info


def sign_request(request: niquests.PreparedRequest, device_id: str, eos_type: str) -> niquests.PreparedRequest:
    eos, license_info = get_eos_instance(eos_type)

    request.headers["User-Agent"] = (f"{eos['clientName']}/{license_info['version']}/{eos['mobileServiceAPIVersion']}/"
                                     f"{eos['identifier']} (Zuegli q@magicalcodewit.ch)")
    request.headers["X-Eos-Date"] = datetime.datetime.now(datetime.UTC).strftime('%a, %d %b %Y %H:%M:%S GMT')
    request.headers["Device-Identifier"] = device_id

    mac_key = eos["applicationKey"].encode("utf-8")
    mac1 = hmac.new(mac_key, request.body, "sha512").hexdigest()
    url = urllib.parse.urlparse(request.url)
    default_port = 443 if url.scheme == "https" else 80
    mac2_msg = f"{mac1}|{url.netloc}|{url.port or default_port}|{url.path}"
    if url.query:
        mac2_msg += f"?{url.query}"
    x_eos_date = request.headers.get("X-Eos-Date", "")
    content_type = request.headers.get("Content-Type", "")
    authorization = request.headers.get("Authorization", "")
    x_eos_anonymous = request.headers.get("X-TICKeos-Anonymous", "")
    x_eos_sso = request.headers.get("X-TICKeos-SSO", "")
    user_agent = request.headers.get("User-Agent", "")
    mac2_msg += f"|{x_eos_date}|{content_type}|{authorization}|{x_eos_anonymous}|{x_eos_sso}|{user_agent}"
    mac2 = hmac.new(mac_key, mac2_msg.encode("utf-8"), "sha512").hexdigest()
    request.headers["X-Api-Signature"] = mac2

    return request


def map_customer_field(f):
    if f["content"]["type"] == "choice":
        if "default" not in f["content"]:
            return None
        return next(filter(lambda c: c["key"] == f["content"]["default"], f["content"]["choices"]))["value"]
    elif f["content"]["type"] == "text":
        return f["content"].get("default")
    elif f["content"]["type"] == "date":
        return datetime.date.fromisoformat(f["content"]["default"]) if "default" in f["content"] else None
    else:
        return None


def login(account: "models.Account", operator: str, username: str, password: str) -> bool:
    _, license_info = get_eos_instance(operator)
    device_id = get_device_id()
    r = session.post(f"{license_info['url_base']}/index.php/mobileService/login", json={
        "credentials": {
            "password": password,
            "username": username,
        }
    }, hooks={
        "pre_request": [lambda req: sign_request(req, device_id, operator)],
    }, timeout=10)
    if not r.ok:
        return False
    auth_data = r.json()
    access_token_data = next(filter(lambda t: t["name"] == "tickeos_access_token", auth_data["authorization_types"]), None)
    if not access_token_data:
        return False
    access_token = "{} {}".format(access_token_data["header"]["type"], access_token_data["header"]["value"])

    models.AccountOAuth.objects.update_or_create(
        account=account,
        provider=operator,
        defaults={
            "token": access_token,
            "device_id": device_id,
        }
    )
    return True


def get_customer_account(account: "models.Account", operator: str):
    _, license_info = get_eos_instance(operator)
    account_token = models.AccountOAuth.objects.get(account=account, provider=operator)

    r = session.post(f"{license_info['url_base']}/index.php/mobileService/customer/fields", json={}, hooks={
        "pre_request": [lambda req: sign_request(req, account_token.device_id, operator)],
    }, headers={
        "Authorization": account_token.token,
    }, timeout=10)
    r.raise_for_status()
    data = r.json()

    return {f["name"]: map_customer_field(f) for b in data["layout_blocks"] for f in b["fields"]}


def update_eos_tickets(account: "models.Account", operator: str):
    _, license_info = get_eos_instance(operator)
    account_token = models.AccountOAuth.objects.filter(account=account, provider=operator).first()
    if not account_token:
        return

    logger.info(f"Updating EOS {account_token.device_id}")

    r = session.post(f"{license_info['url_base']}f", json={}, hooks={
        "pre_request": [lambda req: sign_request(req, account_token.device_id, operator)],
    }, headers={
        "Authorization": account_token.token,
    }, timeout=10)
    if not r.ok:
        logger.error(f"Failed to update EOS {account_token.device_id}: {r.text}")
        return

    data = r.json()

    tickets = []
    for t in data["tickets"]:
        if models.KnownEOSTicket.objects.filter(operator_id=operator, ticket_id=t).exists():
            continue
        else:
            tickets.append(t)

    if tickets:
        r = session.post(f"{license_info['url_base']}/index.php/mobileService/ticket", json={
            "details": True,
            "tickets": tickets,
            "provide_aztec_content": True,
            "parameters": True,
        }, hooks={
            "pre_request": [lambda req: sign_request(req, account_token.device_id, operator)],
        }, headers={
            "Authorization": account_token.token,
        }, timeout=10)
        if not r.ok:
            logger.error(f"Failed to update EOS {account_token.device_id}: {r.text}")
        data = r.json()
        for ticket_id, t in data["tickets"].items():
            if "aztec_content" in t:
                barcode_data = base64.b64decode(t["aztec_content"])
            else:
                template = json.loads(t["template"])

                if "aztec_barcode" in template["content"]["images"]:
                    barcode_img = base64.b64decode(template["content"]["images"]["aztec_barcode"])
                else:
                    barcode_url = None
                    for page in template["content"]["pages"]:
                        ticket_layout = bs4.BeautifulSoup(page, 'html.parser')
                        barcode_elm = ticket_layout.find("img", attrs={
                            "class": "barcode"
                        }, recursive=True)
                        if barcode_elm:
                            barcode_url = barcode_elm.attrs["src"]
                            break

                    if not barcode_url:
                        logger.error("Failed to find barcode")

                    if not barcode_url.startswith("data:"):
                        logger.error("Barcode image not a data URL")
                        continue
                    media_type, data = barcode_url[5:].split(";", 1)
                    encoding, data = data.split(",", 1)
                    if not media_type.startswith("image/"):
                        logger.error("Unsupported media type '%s'", media_type)
                        continue
                    if encoding != "base64":
                        logger.error("Unsupported encoding type '%s' in barcode image", encoding)
                        continue
                    barcode_img = base64.urlsafe_b64decode(data)

                barcode_data = aztec.decode(barcode_img)

            try:
                ticket_obj, _ = ticket.update_from_barcode(barcode_data, account=account)
                ticket_obj.oauth_account = account_token
                ticket_obj.save()
            except ticket.TicketError as e:
                logger.error("Error decoding barcode ticket: %s", e)
                continue

            models.KnownEOSTicket.objects.create(operator_id=operator, ticket_id=ticket_id)

    for t in account_token.tickets.all():
        apn.notify_ticket_if_renewed(t)

    logger.info(f"Successfully updated EOS {account_token.device_id}")
