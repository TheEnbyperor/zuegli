from celery import shared_task
from django.utils import timezone
import django.core.files.storage
import ldap
import json
import niquests
import datetime
import sqlite3
import tempfile
import django.db
import django.db.models.sql
import django.db.models.constants
from main import models, apn, gwallet

BLOCKLIST_VERSION_URL = "https://dt-ion-prod.s3.eu-central-1.amazonaws.com/prod/version.txt"
BLOCKLIST_URL = "https://dt-ion-prod.s3.eu-central-1.amazonaws.com/prod/blacklist.db"


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def download_orgs():
    storage = django.core.files.storage.storages["vdv-certs"]

    r = niquests.get(
        "https://pro.eticket.app/api/organisations/all",
        auth=("eticket-app-pro", "VDV-K3rn4ppl!kat1on"),
        headers={
            "User-Agent": "Zuegli (q@magicalcodewit.ch)",
        },
    )
    r.raise_for_status()
    data = r.json()

    out = {
        "orgs": [],
        "vdv_ids": {},
        "vdv_test_ids": {},
    }

    for org in data["data"]:
        org_pos = len(out["orgs"])
        out["orgs"].append(org)
        if org.get("org_type") == "VDV":
            out["vdv_ids"][org["id"]] = org_pos
            out["vdv_test_ids"][org["test_id"]] = org_pos

    with storage.open("orgs.json", "w") as f:
        json.dump(out, f)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def download_certs():
    certificate_storage = django.core.files.storage.storages["vdv-certs"]

    conn = ldap.initialize("ldaps://ldap-vdv-ion.telesec.de:636")

    conn.search("ou=VDV KA,o=VDV Kernapplikations GmbH,c=de", ldap.SCOPE_SUBTREE, "(objectClass=*)",
                attrlist=["cn", "caCertificate"])
    certs = conn.result()[1]

    for cert in certs:
        attrs = cert[1]
        if "cACertificate" not in attrs:
            continue
        cert_data = attrs["cACertificate"][0]
        common_name = attrs["cn"][0].decode("ascii")

        with certificate_storage.open(f"prod_{common_name}.der", "wb") as f:
            f.write(cert_data)
        print(f"Downloaded {common_name}")

    conn = ldap.initialize("ldaps://vdv.test.telesec.de:636")

    conn.search("ou=VDV Sicherheitsmanagement,o=VDV KA KG,c=de", ldap.SCOPE_SUBTREE, "(objectClass=*)",
                attrlist=["cn", "caCertificate"])
    certs = conn.result()[1]

    for cert in certs:
        attrs = cert[1]
        if "cACertificate" not in attrs:
            continue
        cert_data = attrs["cACertificate"][0]
        common_name = attrs["cn"][0].decode("ascii")

        with certificate_storage.open(f"test_{common_name}.der", "wb") as f:
            f.write(cert_data)
        print(f"Downloaded {common_name}")


def map_item_type(item_type):
    if item_type == "A":
        return models.VDVBlocklistItem.ITEM_NUTZERMEDIUM
    elif item_type == "B":
        return models.VDVBlocklistItem.ITEM_BERECHTIGUNG
    else:
        raise ValueError(f"Unknown item type {item_type}")


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def sync_blocklist():
    blocklist_meta = models.VDVBlocklistMeta.get_solo()

    r = niquests.get(BLOCKLIST_VERSION_URL, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    })
    r.raise_for_status()
    latest_blocklist_version = datetime.datetime.fromisoformat(r.text).astimezone(datetime.timezone.utc)

    if blocklist_meta.current_version and blocklist_meta.current_version >= latest_blocklist_version:
        print("Blocklist already up to date")
        return

    db_file = tempfile.NamedTemporaryFile(delete_on_close=False)

    r = niquests.get(BLOCKLIST_URL, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)",
    }, stream=True)
    r.raise_for_status()

    for chunk in r.iter_content(chunk_size=128):
        db_file.write(chunk)

    db_file.flush()
    db_file.close()

    db = sqlite3.connect(db_file.name)

    cursor = db.cursor()

    now = timezone.now()

    cursor.execute("SELECT COUNT(*) FROM blacklist")
    res = cursor.fetchone()
    total = res[0]

    cursor.execute("SELECT type, orgId, number, instanceNum, lockMode FROM blacklist")
    processed = 0
    new_entries_count = 0
    next_print = 250
    batch_size = 2500
    while batch := cursor.fetchmany(batch_size):
        values = [(map_item_type(row[0]), row[1], row[2], row[3], row[4], now) for row in batch]
        value_placeholders = ", ".join(["(%s, %s, %s, %s, %s, %s)" for _ in batch])
        query = f"""
                INSERT INTO {models.VDVBlocklistItem._meta.db_table} (item_type, org_id, item_id, instance_counter, lock_mode, timestamp)
                VALUES {value_placeholders}
                ON CONFLICT DO NOTHING
                RETURNING org_id, item_id
            """
        with django.db.connection.cursor() as dc:
            dc.execute(query, [c for v in values for c in v])
            new_entries = dc.fetchall()
            new_entries_count += len(new_entries)

        for org_id, item_id in new_entries:
            i = models.VDVTicketInstance.objects.filter(ticket_org_id=org_id, ticket_num=item_id).first()
            if not i:
                continue
            ticket = i.ticket
            print(f"Force updating ticket {ticket.public_id()}")
            ticket.last_updated = timezone.now()
            ticket.save()
            apn.notify_ticket.delay(ticket.pk)
            gwallet.sync_ticket.delay(ticket.pk)

        processed += len(batch)
        if processed >= next_print:
            next_print += 250
            print(f"Processed {processed} of {total} items - {new_entries_count} new", flush=True)

    print(f"Processed {processed} of {total} items - {new_entries_count} new", flush=True)

    blocklist_meta.current_version = latest_blocklist_version
    blocklist_meta.save()
