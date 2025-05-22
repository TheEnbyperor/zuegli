from django.core.management.base import BaseCommand
import niquests
import datetime
import sqlite3
import tempfile
import django.db
import django.db.models.sql
import django.db.models.constants
from django.utils import timezone
from main import models, apn, gwallet

BLOCKLIST_VERSION_URL = "https://dt-ion-prod.s3.eu-central-1.amazonaws.com/prod/version.txt"
BLOCKLIST_URL = "https://dt-ion-prod.s3.eu-central-1.amazonaws.com/prod/blacklist.db"


class Command(BaseCommand):
    help = "Pull latest "

    @staticmethod
    def map_item_type(item_type):
        if item_type == "A":
            return models.VDVBlocklistItem.ITEM_NUTZERMEDIUM
        elif item_type == "B":
            return models.VDVBlocklistItem.ITEM_BERECHTIGUNG
        else:
            raise ValueError(f"Unknown item type {item_type}")

    def handle(self, *args, **options):
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
            values = [(self.map_item_type(row[0]), row[1], row[2], row[3], row[4], now) for row in batch]
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
