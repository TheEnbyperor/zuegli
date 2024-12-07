from django.core.management.base import BaseCommand
from django.db import transaction
import django.core.files.storage
import csv
from main import models

class Command(BaseCommand):
    help = "Sync ZHV data into database"

    def handle(self, *args, **options):
        storage = django.core.files.storage.storages["vdv-certs"]

        with storage.open("zHV_aktuell.csv", "r") as f:
            data = csv.DictReader(f, delimiter=";")
            for row in data:
                dhid_parts = row["DHID"].split(":")
                with transaction.atomic():
                    models.ZHVStop.objects.update_or_create(
                        dhid=row["DHID"],
                        defaults={
                            "dhid_raw_id": ":".join(dhid_parts[2:]),
                            "parent_id": row["Parent"] if row["Parent"] != row["DHID"] else None,
                            "name": row["Name"],
                            "longitude": float(row["Longitude"].replace(",", ".")),
                            "latitude": float(row["Latitude"].replace(",", ".")),
                            "municipality": row["Municipality"],
                            "district": row["District"],
                            "description": row["Description"],
                            "authority": row["Authority"],
                            "thid": row["THID"],
                        },
                    )