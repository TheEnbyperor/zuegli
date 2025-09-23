from django.core.management.base import BaseCommand
from celery import shared_task
from django.conf import settings
import django.core.files.storage
import niquests
import xsdata.formats.dataclass.parsers
import xsdata.models.datatype
import json
import csv
import datetime
import main.uic.gen.bar_code_key_exchange

xml_parser = xsdata.formats.dataclass.parsers.XmlParser()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def download_data():
    uic_storage = django.core.files.storage.storages["uic-data"]

    rics_codes_r = niquests.get("https://teleref.era.europa.eu/Download_CompanycodesExcel.aspx", headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    })
    rics_codes_r.raise_for_status()
    rics_codes = csv.DictReader(rics_codes_r.text.splitlines(), delimiter="\t")

    out = {}
    for row in rics_codes:
        out[int(row["Company Code"])] = {
            "short_name": row["Short Name"],
            "full_name": row["Name"],
            "country": row["Country"],
            "add_date": datetime.datetime.strptime(row["Add Date"], "%d-%m-%y").date().isoformat(),
            "modify_date": datetime.datetime.strptime(row["Mod Date"], "%d-%m-%y").date().isoformat()
            if row["Mod Date"] else None,
            "start_validity": datetime.datetime.strptime(row["Start Validity"], "%d-%m-%y").date().isoformat(),
            "end_validity": datetime.datetime.strptime(row["End Validity"], "%d-%m-%y").date().isoformat()
            if row["End Validity"] else None,
            "type": {
                "freight": row["Freight"] == "x",
                "passenger": row["Passenger"] == "x",
                "infrastructure": row["Infrastructure"] == "x",
                "other": row["Other Company"] == "x",
            },
            "url": row["URL"] if row["URL"] else None,
        }

    with uic_storage.open("rics_codes.json", "w") as f:
        json.dump(out, f)

    stations_r = niquests.get("https://api.kontrolor.si/stations", headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    })
    stations_r.raise_for_status()
    out = {
        "stations": [],
        "uic_codes": {}
    }
    for row in stations_r.json():
        row["uic"] = row["uicId"]
        del row["uicId"]
        out["stations"].append(row)
        i = len(out["stations"]) - 1
        out["uic_codes"][row["uic"]] = i

    with uic_storage.open("uic-stations.json", "w") as f:
        json.dump(out, f)

    stations_r = niquests.get("https://github.com/trainline-eu/stations/raw/refs/heads/master/stations.csv",
                              headers={
                                  "User-Agent": "Zuegli (q@magicalcodewit.ch)",
                              })
    stations_r.raise_for_status()
    stations = csv.DictReader(stations_r.text.splitlines(), delimiter=";")

    out = {
        "stations": [],
        "uic_codes": {},
        "uic_sncf_codes": {},
        "db_ids": {},
        "sncf_ids": {},
        "benerail_ids": {}
    }
    for row in stations:
        station = {}
        for k, v in row.items():
            if v == "t":
                station[k] = True
            elif v == "f":
                station[k] = False
            elif v:
                station[k] = v
        out["stations"].append(station)
        i = len(out["stations"]) - 1
        if row["uic"]:
            out["uic_codes"][row["uic"]] = i
        if row["uic8_sncf"]:
            out["uic_sncf_codes"][row["uic8_sncf"]] = i
        if row["db_id"]:
            out["db_ids"][row["db_id"]] = i
        if row["benerail_id"]:
            out["benerail_ids"][row["benerail_id"]] = i
        if row["sncf_id"]:
            out["sncf_ids"][row["sncf_id"]] = i

    with uic_storage.open("stations.json", "w") as f:
        json.dump(out, f)

    finnish_stations_r = niquests.get("https://rata.digitraffic.fi/api/v1/metadata/stations")
    finnish_stations_r.raise_for_status()

    out = {
        "stations": [],
        "station_codes": {},
    }
    for station in finnish_stations_r.json():
        out["stations"].append(station)
        i = len(out["stations"]) - 1
        out["station_codes"][station["stationShortCode"]] = i

    with uic_storage.open("finnish-stations.json", "w") as f:
        json.dump(out, f)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def download_certs():
    uic_storage = django.core.files.storage.storages["uic-data"]

    r = niquests.get("https://railpublickey.uic.org/download.php")
    r.raise_for_status()

    data = xml_parser.from_string(r.text, main.uic.gen.bar_code_key_exchange.Keys)
    for key in data.key:
        if key.public_key.keytype != "CERTIFICATE":
            continue
        key_name = f"cert-{key.issuer_code}_{key.id}.der"
        key_meta_name = f"cert-{key.issuer_code}_{key.id}.json"
        with uic_storage.open(key_name, "wb") as f:
            f.write(key.public_key.value)
        with uic_storage.open(key_meta_name, "w") as f:
            json.dump({
                "issuer_name": key.issuer_name,
                "issuer_code": key.issuer_code,
                "version_type": key.version_type,
                "signature_algorithm": key.signature_algorithm,
                "key_id": key.id,
                "barcode_version": key.barcode_version,
                "start_date": key.start_date.to_date().isoformat(),
                "end_date": key.end_date.to_date().isoformat(),
                "allowed_product_owner_codes": key.allowed_product_owner_codes.product_owner_code if key.allowed_product_owner_codes.product_owner_code else None,
                "allowed_product_owner_name": key.allowed_product_owner_codes.product_owner_name if key.allowed_product_owner_codes.product_owner_name else None,
            }, f)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def download_db_stations():
    storage = django.core.files.storage.storages["uic-data"]

    r = niquests.get("https://apis.deutschebahn.com/db-api-marketplace/apis/station-data/v2/stations", headers={
        "DB-Client-ID": settings.DB_CLIENT_ID,
        "DB-Api-Key": settings.DB_API_KEY,
    })
    r.raise_for_status()
    data = r.json()["result"]

    out = {
        "stations": [],
        "db_ids": {},
    }
    for row in data:
        out["stations"].append(row)
        i = len(out["stations"]) - 1

    with storage.open("db-stations.json", "w") as f:
        json.dump(out, f)
