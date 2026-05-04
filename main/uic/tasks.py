from django.core.management.base import BaseCommand
from celery import shared_task
from django.conf import settings
from django.utils import timezone
import django.core.files.storage
import niquests
import xsdata.formats.dataclass.parsers
import xsdata.models.datatype
import json
import csv
import datetime
import tempfile
import zipfile
import openpyxl_dictreader
import io
import main.uic.gen.bar_code_key_exchange
from .. import models, apn, gwallet

xml_parser = xsdata.formats.dataclass.parsers.XmlParser()


DTVG_BLOCKLIST_VERSION_URL = "https://dt-ion-prod.s3.eu-central-1.amazonaws.com/prod/versionuic.txt"
DTVG_BLOCKLIST_URL = "https://dt-ion-prod.s3.eu-central-1.amazonaws.com/prod/blacklistuic.zip"


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def download_data():
    uic_storage = django.core.files.storage.storages["uic-data"]

    codes_r = niquests.get("https://teleref.era.europa.eu/DownloadOrganizationCodes.aspx", headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    })
    codes_r.raise_for_status()
    codes_reader = openpyxl_dictreader.DictReader(io.BytesIO(codes_r.content), "Organisation codes")

    out = {}
    for row in codes_reader:
        out[row["Organisation code"]] = {
            "short_name": row["Acronym"],
            "full_name": row["Organisation Name / Legal denomination"],
            "country": row["Country"],
            "add_date": row["Date of allocation"].date().isoformat(),
            "domains": row["Domains of activity"],
            "url": row["Website"] if row["Website"] else None,
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
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
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
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
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

@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def sync_dtvg_blocklist():
    blocklist_meta = models.DTVGBlocklistMeta.get_solo()

    r = niquests.get(DTVG_BLOCKLIST_VERSION_URL, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    })
    r.raise_for_status()
    latest_blocklist_version = int(r.json()["blacklistId"])

    if blocklist_meta.current_version >= latest_blocklist_version:
        print("Blocklist already up to date")
        return

    db_file = tempfile.NamedTemporaryFile(delete_on_close=False)

    r = niquests.get(DTVG_BLOCKLIST_URL, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    }, stream=True)
    r.raise_for_status()

    for chunk in r.iter_content(chunk_size=128):
        db_file.write(chunk)

    db_file.seek(0)
    zip_file = zipfile.ZipFile(db_file)
    blocklist = csv.DictReader(io.TextIOWrapper(zip_file.open("blacklistuic.csv"), "utf-8-sig"))
    now = timezone.now()
    total_entries = 0
    new_entries_count = 0
    for chunk in batch(blocklist, 2500):
        total_entries += len(chunk)
        values = [(int(block["rics"]), block["ticketId"], now) for block in chunk]
        value_placeholders = ", ".join(["(%s, %s, %s)" for _ in chunk])
        query = f"""
            INSERT INTO {models.DTVGBlocklistItem._meta.db_table} (rics, ticket_id, timestamp)
            VALUES {value_placeholders}
            ON CONFLICT DO NOTHING
            RETURNING rics, ticket_id
        """
        with django.db.connection.cursor() as dc:
            dc.execute(query, [c for v in values for c in v])
            new_entries = dc.fetchall()
            new_entries_count += len(new_entries)

        for rics, ticket_id in new_entries:
            print(f"New blocklist entry for {rics}: #{ticket_id}")
            i = models.UICTicketInstance.objects.filter(distributor_rics=rics, ticket_pnr=ticket_id).first()
            if not i:
                continue
            ticket = i.ticket
            print(f"Force updating ticket {ticket.public_id()}")
            ticket.last_updated = timezone.now()
            ticket.save()
            apn.notify_ticket.delay(ticket.pk)
            gwallet.sync_ticket.delay(ticket.pk)

    print(f"Processed {total_entries} items - {new_entries_count} new", flush=True)

    blocklist_meta.current_version = latest_blocklist_version
    blocklist_meta.save()


def batch(iterable, n=1):
    chunk = []
    for block in iterable:
        chunk.append(block)
        if len(chunk) >= 1:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
