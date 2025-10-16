import secrets
from celery import shared_task
import django.core.files.storage
import niquests
import niquests.adapters
import urllib3.util
import json
import main.flexi_ticket.crypto

retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)

BRANDS = [{
    "id": "MBTA",
    "key": {
        "modulus": "a334171ba88b3df1e02c5d245a8b0380acf30ffc8f1b52c01ddd31e7df41f47d066378408811c8e8c3e43efa8491e8cb837b36a4e83dfe671fce9ad3bd41b0e1e4ff78bb80b2376e985b96c5f097899f03e31fb68d24e1d0821a6a2e26e5b9a2bee7995c643233eaf054aad7799b972f68bba3c9c4ef24d2d21b81117b31637b",
        "exponent": "10001"
    }
}, {
    "id": "RTDDENVER",
    "key": {
        "modulus": "9a389610cf547a8e7f576c1fd7d131b117762dfaabb336760e59efedd7f2bbbc35776841ec7a2350e65bf5891203fcf65c835b817f6d6119e4675b50ee9c54947318c7df6a2ad9caaf689dbfb3a4301f0b392fb71592dbe3cafb39e4b2b3bb5eae8f5ed08fbea93bc8aaa51dda86adc0b58d5542c33a9bdeacc12a2651d4d609",
        "exponent": "10001"
    }
}, {
    "id": "MTA",
    "key": {
        "modulus": "c83a357f7179b1b7101afa930d9ce81d026bf493ce93dc7cccbf716ea6f69d49fc3bde3450b8e7a3061fced4c6342853032ce34a7c76c6dd5f4f546809e77237dc4dcf12283f67a49e35c23a10b958d86a7797d770bbffcf22a0cc1c687814da29bddd19a587b9afcd287fa58beec7ad0d332456f1d8976ce32eaa11597366f7",
        "exponent": "10001"
    }
}, {
    "id": "ML",
    "key": {
        "modulus": "835aa8f162d9340ae454e012cb387b3d3df540c653ff74698fc62d08158b8cac5abb8ca17bd8afd994a01152bb68c01c38f9d8cdd6a685d4d65d06d08f0aac626ece6c4987522dc227e1f4bd8821c11f6dca3c79ba3015d21d99cabf053840adf7cc6a38cb4455b1bc8fc5567faaf3a46f9bff743da4e17a0fb07fd170cacfcb",
        "exponent": "10001"
    }
}]


def make_request(session, url: str, data: dict, key: dict) -> dict:
    modulus = int(key["modulus"], 16)
    exponent = int(key["exponent"], 16)
    data = json.dumps(data).encode("utf-8")
    aes_key = secrets.token_bytes(32)
    encrypted = main.flexi_ticket.crypto.aes_encrypt_and_prepend_key(aes_key, data)
    decrypt_iv = encrypted[-16:]
    encrypted = main.flexi_ticket.crypto.rsa(encrypted, exponent, modulus)
    r = session.post(url, headers={
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    }, data=encrypted)
    r.raise_for_status()
    decrypted = main.flexi_ticket.crypto.aes_decrypt(aes_key, r.content, decrypt_iv)
    decrypted = decrypted.decode("utf-8")
    return json.loads(decrypted)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def download_ft_data():
    ft_storage = django.core.files.storage.storages["ft-data"]
    adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
    session = niquests.Session()
    session.mount("https://", adapter)

    for brand in BRANDS:
        install = make_request(
            session,
            f"https://us-app.justride.com/edge/broker/enc/rest/V3.5/{brand['id']}/device/install", {
                "appId": None,
                "password": "This is a simple app to download all your data :)",
                "header": {
                    "appId": None,
                    "brandId": brand["id"],
                    "sessionToken": None
                }
            }, brand["key"])

        stations_r = session.get(
            f"https://us-app.justride.com/edge/brandconfig/v/1/{brand['id']}/stations",
            headers={
                "User-Agent": "Zuegli (q@magicalcodewit.ch)",
            }
        )
        stations_r.raise_for_status()
        stations = stations_r.json()

        out = {
            "stations": {},
            "products": {},
        }
        for station in stations["stations"]:
            out["stations"][station["id"]] = station

        selection_keys = set()
        for s in stations["selectionKeyOptions"]:
            for k in s["keySet"]:
                for a in stations["stations"]:
                    for b in stations["stations"]:
                        selection_keys.add(
                            k.replace("%O%", str(a["id"]))
                            .replace("%D%", str(b["id"]))
                        )

        selection_keys.update((
            "EXTENSION",
            "DISCRETE",
            "Hidden",
            "SE",
            "AURARIA",
            "AURARIAS22",
            "AURARIAS23",
            "AURARIAS24",
            "ABT",
            "ECOPASS",
            "NECOPASS",
            "COLLEGEPASS",
            "COLLEGEPASSCUBOULDER",
            "ECOPASSAURARIA",
            "SemesterPass"
        ))

        selection_keys = list(selection_keys)
        for i in range(0, len(selection_keys), 1000):
            request = {
                "criteria": {
                    "data": [{
                        "stepId": "selectionKeys",
                        "value": selection_keys[i:i + 1000]
                    }]
                },
                "header": {
                    "appId": install["header"]["appId"],
                    "brandId": brand["id"],
                    "sessionToken": install["header"]["sessionToken"]
                },
            }
            res = make_request(
                session,
                f"https://us-app.justride.com/edge/broker/enc/rest/V3.5/{brand['id']}/lookup/product",
                request, brand["key"]
            )
            for product in res['lookupData']:
                if product["externalProductReference"] not in out["products"]:
                    out["products"][product["externalProductReference"]] = {
                        "name": product["name"],
                    }

        with ft_storage.open(f"{brand['id']}.json", "w") as f:
            json.dump(out, f)
