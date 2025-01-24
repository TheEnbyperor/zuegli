from django.core.management.base import BaseCommand
import django.core.files.storage
import niquests
import csv
import datetime
import json


class Command(BaseCommand):
    help = "Download UIC data from the ERA and Trainline"

    def handle(self, *args, **options):
        uic_storage = django.core.files.storage.storages["uic-data"]

        rics_codes_r = niquests.get("https://teleref.era.europa.eu/Download_CompanycodesExcel.aspx", headers={
            "User-Agent": "VDV PKPass Generator (magicalcodewit.ch)",
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
            "User-Agent": "VDV PKPass Generator (magicalcodewit.ch)",
        })
        stations_r.raise_for_status()
        out = {
            "stations": [],
            "uic_codes": {}
        }
        for row in stations_r.json():
            out["stations"].append(row)
            i = len(out["stations"]) - 1
            out["uic_codes"][row["uicId"]] = i

        with uic_storage.open("uic-stations.json", "w") as f:
            json.dump(out, f)

        stations_r = niquests.get("https://github.com/trainline-eu/stations/raw/refs/heads/master/stations.csv", headers={
            "User-Agent": "VDV PKPass Generator (magicalcodewit.ch)",
        })
        stations_r.raise_for_status()
        stations = csv.DictReader(stations_r.text.splitlines(), delimiter=";")

        out = {
            "db_ids": {},
            "sncf_ids": {},
            "benerail_ids": {}
        }
        for row in stations:
            if row["uic"]:
                if row["db_id"]:
                    out["db_ids"][row["db_id"]] = row["uic"]
                if row["benerail_id"]:
                    out["benerail_ids"][row["benerail_id"]] = row["uic"]
                if row["sncf_id"]:
                    out["sncf_ids"][row["sncf_id"]] = row["uic"]

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