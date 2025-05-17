from django.core.management.base import BaseCommand
import niquests
import datetime
import sqlite3
import tempfile
import itertools
from main import models

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

        cursor.execute("SELECT COUNT(*) FROM blacklist")
        res = cursor.fetchone()
        total = res[0]

        cursor.execute("SELECT type, orgId, number, instanceNum, lockMode FROM blacklist")
        processed = 0
        next_print = 250
        batch_size = 2500
        while batch := cursor.fetchmany(batch_size):
            objs = models.VDVBlocklistItem.objects.bulk_create(
                [
                    models.VDVBlocklistItem(
                        item_type=self.map_item_type(row[0]),
                        kvp_org_id=row[1],
                        item_id=row[2],
                        instance_counter=row[3],
                        lock_mode=row[4],
                    ) for row in batch
                ], batch_size=batch_size, ignore_conflicts=True
            )
            processed += len(objs)
            if processed >= next_print:
                next_print += 250
                print(f"Processed {processed} of {total} items", flush=True)

        print(f"Processed {processed} of {total} items", flush=True)

        blocklist_meta.current_version = latest_blocklist_version
        blocklist_meta.save()
