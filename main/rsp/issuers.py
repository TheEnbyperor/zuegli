import csv
import django.core.files.storage

ISSUERS = None

def get_issuers():
    global ISSUERS

    if ISSUERS is not None:
        return ISSUERS

    ISSUERS = {
        "live": {},
        "test": {}
    }

    rsp_storage = django.core.files.storage.storages["rsp-data"]
    with rsp_storage.open("issuers.txt") as f:
        data = csv.DictReader(
            map(lambda r: r.decode("utf-8"), f.readlines()),
            delimiter="\t",
            fieldnames=["uid", "full_name", "short_name", "env", "id"]
        )
        for issuer in data:
            ISSUERS[issuer["env"].lower()][issuer["id"]] = {
                "short_name": issuer["short_name"],
                "full_name": issuer["full_name"],
                "live": issuer["env"] == "Live",
            }

    return ISSUERS

def issuer_name(code: str) -> str:
    data = get_issuers()
    if code in data["live"]:
        return data["live"][code]["full_name"]
    else:
        return f"Unknown - {code}"