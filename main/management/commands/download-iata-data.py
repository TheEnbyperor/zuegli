from django.core.management.base import BaseCommand
import django.core.files.storage
import niquests
import csv
import datetime
import json


class Command(BaseCommand):
    help = "Download UIC data from the ERA and Trainline"

    def handle(self, *args, **options):
        iata_storage = django.core.files.storage.storages["iata-data"]

        airports_r = niquests.get("https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports-extended.dat", headers={
            "User-Agent": "VDV PKPass Generator (magicalcodewit.ch)",
        })
        airports_r.raise_for_status()
        airports = csv.DictReader(
            airports_r.text.splitlines(),
            fieldnames=(
                "id", "name", "city", "country", "iata_code", "icao_code", "latitude", "longitude", "altitude",
                "timezone", "dst", "tz_name", "type", "source"
            )
        )

        out = {
            "airports": [],
            "iata_codes": {},
            "icao_codes": {},
        }
        for row in airports:
            if row["iata_code"] == "\\N":
                row["iata_code"] = None
            if row["icao_code"] == "\\N":
                row["icao_code"] = None
            if row["timezone"] == "\\N":
                row["timezone"] = None
            if row["dst"] == "\\N":
                row["dst"] = None
            if row["tz_name"] == "\\N":
                row["tz_name"] = None
            if row["type"] == "\\N":
                row["type"] = None
            if row["source"] == "\\N":
                row["source"] = None
            out["airports"].append(row)
            i = len(out["airports"]) - 1
            if row["iata_code"]:
                if row["iata_code"] not in out["iata_codes"]:
                    out["iata_codes"][row["iata_code"]] = i
            if row["icao_code"]:
                if row["icao_code"] not in out["icao_codes"]:
                    out["icao_codes"][row["icao_code"]] = i

        with iata_storage.open("airports.json", "w") as f:
            json.dump(out, f)

        airlines_r = niquests.get("https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat", headers={
            "User-Agent": "VDV PKPass Generator (magicalcodewit.ch)",
        })
        airlines_r.raise_for_status()
        airlines = csv.DictReader(
            airlines_r.text.splitlines(),
            fieldnames=("id", "name", "alias", "iata_code", "icao_code", "callsign", "country", "active")
        )

        out = {
            "airlines": [],
            "iata_codes": {},
            "icao_codes": {},
        }
        for row in airlines:
            if row["alias"] == "\\N":
                row["alias"] = None
            if row["iata_code"] == "\\N":
                row["iata_code"] = None
            if row["icao_code"] == "\\N":
                row["icao_code"] = None
            if row["callsign"] == "\\N":
                row["callsign"] = None
            out["airlines"].append(row)
            i = len(out["airlines"]) - 1
            if row["iata_code"]:
                if row["iata_code"] not in out["iata_codes"]:
                    out["iata_codes"][row["iata_code"]] = i
            if row["icao_code"]:
                if row["icao_code"] not in out["icao_codes"]:
                    out["icao_codes"][row["icao_code"]] = i

        with iata_storage.open("airlines.json", "w") as f:
            json.dump(out, f)
