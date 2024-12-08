from django.core.management.base import BaseCommand
import django.core.files.storage
import csv
import itertools
from main import models

class Command(BaseCommand):
    help = "Sync ZHV data into database"

    def handle(self, *args, **options):
        storage = django.core.files.storage.storages["vdv-certs"]

        with storage.open("zHV_aktuell.csv", "r") as f:
            data = csv.DictReader(f, delimiter=";")
            for batch in itertools.batched(data, 1000):
                models.ZHVStop.objects.bulk_create(
                    [models.ZHVStop(
                        dhid=row["DHID"],
                        dhid_raw_id=":".join(row["DHID"].split(":")),
                        parent_id=row["Parent"] if row["Parent"] != row["DHID"] else None,
                        name=row["Name"],
                        longitude=float(row["Longitude"].replace(",", ".")),
                        latitude=float(row["Latitude"].replace(",", ".")),
                        municipality=row["Municipality"],
                        district=row["District"],
                        description=row["Description"],
                        authority=row["Authority"],
                        thid=row["THID"],
                    ) for row in batch],
                    update_conflicts=True,
                    unique_fields=["dhid"],
                    update_fields=[
                        "dhid_raw_id", "parent_id", "name", "longitude",
                        "latitude", "municipality", "district", "description",
                        "authority", "thid"
                    ],
                )