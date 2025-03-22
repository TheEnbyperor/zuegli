from django.conf import settings
from django.core.management.base import BaseCommand
import django.core.files.storage
import niquests
import json

class Command(BaseCommand):
    help = "Download Deutsche Bahn station data"

    def handle(self, *args, **options):
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
