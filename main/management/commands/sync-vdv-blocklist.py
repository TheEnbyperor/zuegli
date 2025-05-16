from django.core.management.base import BaseCommand
import niquests
import datetime
import sqlite3
import tempfile
from main import models

BLOCKLIST_VERSION_URL = "https://dt-ion-prod.s3.eu-central-1.amazonaws.com/prod/version.txt"
BLOCKLIST_URL = "https://dt-ion-prod.s3.eu-central-1.amazonaws.com/prod/blacklist.db"


class Command(BaseCommand):
    help = "Pull latest "

    def handle(self, *args, **options):
        blocklist_meta = models.VDVBlocklistMeta.get_solo()

        r = niquests.get(BLOCKLIST_VERSION_URL, headers={
            "User-Agent": "Zuegli (q@magicalcodewit.ch)",
        })
        r.raise_for_status()
        latest_blocklist_version = datetime.datetime.fromisoformat(r.text)

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
        cursor.execute("SELECT type, orgId, number, instanceNum, lockMode FROM blacklist")
        for row in cursor.fetchall():
            item_type, kvp_org_id, number, instance_num, lock_mode = row

            if item_type == "A":
                item_type = models.VDVBlocklistItem.ITEM_NUTZERMEDIUM
            elif item_type == "B":
                item_type = models.VDVBlocklistItem.ITEM_BERECHTIGUNG
            else:
                print(f"Unknown item type {item_type}")
                return

            if models.VDVBlocklistItem.objects.filter(
                    item_type=item_type, kvp_org_id=kvp_org_id, item_id=number, instance_counter=instance_num
            ).count() > 0:
                continue

            blacklist_item, _ = models.VDVBlocklistItem.objects.get_or_create(
                item_type=item_type,
                kvp_org_id=kvp_org_id,
                item_id=number,
            )
            if blacklist_item.instance_counter < instance_num:
                blacklist_item.instance_counter = instance_num
                blacklist_item.lock_mode = lock_mode
                blacklist_item.save()

        blocklist_meta.current_version = latest_blocklist_version
        blocklist_meta.save()
