import niquests
import secrets
import hashlib
import json
import datetime
import hmac
import urllib.parse
from Crypto.Cipher import AES
from django.core.files.storage import storages


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
    EOS_INSTANCES[eos_type] = eos_instance, license_info["version"]
    return eos_instance, license_info["version"]


def sign_request(request: niquests.PreparedRequest, device_id: str, eos_type: str) -> niquests.PreparedRequest:
    eos, version = get_eos_instance(eos_type)

    request.headers["User-Agent"] = (f"{eos['clientName']}/{version}/{eos['mobileServiceAPIVersion']}/"
                                     f"{eos['identifier']} (VDV PKPass q@magicalcodewit.ch)")
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
        return datetime.date.fromisoformat(f["content"]["default"])
