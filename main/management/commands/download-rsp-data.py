import zipfile
import io
from django.utils import timezone
from django.conf import settings
from django.core.management.base import BaseCommand
import django.core.files.storage
import niquests
import xsdata.formats.dataclass.parsers
import xsdata.formats.dataclass.parsers.config
import xsdata.formats.dataclass.serializers
import xsdata.models.datatype
import json
import datetime
import csv
import main.rsp.gen.nre_ticket_v4_0

xml_parser = xsdata.formats.dataclass.parsers.XmlParser(config=xsdata.formats.dataclass.parsers.config.ParserConfig(
    fail_on_unknown_properties=False,
))
serializer = xsdata.formats.dataclass.serializers.JsonSerializer()

class Command(BaseCommand):
    help = "Download RDG RSP data"

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()
        storage = django.core.files.storage.storages["rsp-data"]

        r = niquests.post("https://opendata.nationalrail.co.uk/authenticate", data={
            "username": settings.NR_USERNAME,
            "password": settings.NR_PASSWORD,
        })
        r.raise_for_status()
        nre_token = r.json()["token"]

        r = niquests.get("https://opendata.nationalrail.co.uk/api/staticfeeds/2.0/fares", headers={
            "X-Auth-Token": nre_token,
        })
        fares_zip = zipfile.ZipFile(io.BytesIO(r.content))
        r = niquests.get("https://opendata.nationalrail.co.uk/api/staticfeeds/2.0/routeing", headers={
            "X-Auth-Token": nre_token,
        })
        routeing_zip = zipfile.ZipFile(io.BytesIO(r.content))
        discounts_file_name = next(filter(lambda n: n.split(".")[1] == "DIS", fares_zip.namelist()))
        routes_file_name = next(filter(lambda n: n.split(".")[1] == "RTE", fares_zip.namelist()))
        toc_file_name = next(filter(lambda n: n.split(".")[1] == "TOC", fares_zip.namelist()))
        routes_2_file_name = next(filter(lambda n: n.split(".")[1] == "RGK", routeing_zip.namelist()))

        routes = {}
        exclusions = []
        with fares_zip.open(routes_file_name) as f:
            for line in f.readlines():
                if line[0] != 82:  # R
                    continue
                route_code = int(line[2:7].decode("ascii"))
                end_date = datetime.datetime.strptime(line[7:15].decode("ascii"), "%d%m%Y").date()
                if line[1] == 82:
                    start_date = datetime.datetime.strptime(line[15:23].decode("ascii"), "%d%m%Y").date()
                    if start_date > today or end_date < today:
                        continue

                    quote_date = datetime.datetime.strptime(line[23:31].decode("ascii"), "%d%m%Y").date()
                    description = line[31:47].decode("utf-8").strip()
                    atb_desc_1 = line[47:82].decode("utf-8").strip()
                    atb_desc_2 = line[82:117].decode("utf-8").strip()
                    atb_desc_3 = line[117:152].decode("utf-8").strip()
                    atb_desc_4 = line[152:187].decode("utf-8").strip()
                    cc_desc = line[187:203].decode("utf-8").strip()
                    aaa_desc = line[203:244].decode("utf-8").strip()

                    routes[route_code] = {
                        "start_date": start_date.isoformat() if start_date.year != 2999 else None,
                        "end_date": end_date.isoformat() if end_date.year != 2999 else None,
                        "quote_date": quote_date.isoformat() if quote_date.year != 2999 else None,
                        "description": description,
                        "atb_desc": f"{atb_desc_1}\n{atb_desc_2}\n{atb_desc_3}\n{atb_desc_4}".strip(),
                        "cc_desc": cc_desc,
                        "aaa_desc": aaa_desc,
                        "exclusions": [],
                        "inclusions": [],
                        "all_included_crs": [],
                        "any_included_crs": [],
                        "excluded_crs": [],
                        "included_modes": [],
                        "excluded_modes": [],
                        "included_tocs": [],
                        "excluded_tocs": [],
                    }
                elif line[1] == 76:  # L
                    if end_date < today:
                        continue

                    admin_area_code = line[15:18].decode("utf-8").strip()
                    try:
                        nlc = int(line[18:22].decode("ascii"))
                    except ValueError:
                        continue
                    crs = line[22:25].decode("ascii").strip()
                    inc_exl = chr(line[25])
                    exclusions.append((inc_exl, route_code, {
                        "end_date": end_date.isoformat() if end_date.year != 2999 else None,
                        "admin_area_code": admin_area_code,
                        "nlc": nlc,
                        "crs": crs,
                    }))

        for inc_exl, route, line in exclusions:
            if inc_exl == "I":
                routes[route]["inclusions"].append(line)
            elif inc_exl == "E":
                routes[route]["exclusions"].append(line)

        discounts = {}
        with fares_zip.open(discounts_file_name) as f:
            for line in f.readlines():
                if line[0] != 83:  # S
                    continue
                discount_code = int(line[1:4].decode("ascii"))
                end_date = datetime.datetime.strptime(line[5:12].decode("ascii"), "%d%m%Y").date()
                start_date = datetime.datetime.strptime(line[12:20].decode("ascii"), "%d%m%Y").date()
                if start_date > today or end_date < today:
                    continue
                description = line[25:30].decode("utf-8").strip()
                discounts[discount_code] = {
                    "start_date": start_date.isoformat() if start_date.year != 2999 else None,
                    "end_date": end_date.isoformat() if end_date.year != 2999 else None,
                    "description": description,
                }

        with storage.open("discounts.json", "w") as f:
            json.dump(discounts, f)

        tocs = {}
        with fares_zip.open(toc_file_name) as f:
            for line in f.readlines():
                if line[0] != 84:  # T
                    continue
                toc_id = line[1:3].decode("ascii")
                toc_name = line[3:33].decode("ascii")
                tocs[toc_id] = {
                    "name": toc_name,
                }

        with storage.open("tocs.json", "w") as f:
            json.dump(tocs, f)

        with routeing_zip.open(routes_2_file_name) as f:
            d = csv.DictReader(
                map(lambda r: r.decode("utf-8"), filter(lambda r: r[0] != 47, f.readlines())),
                fieldnames=["route_code", "record_type", "entry_type", "crs_code", "group_mkr", "mode_code", "toc_id"]
            )
            for row in d:
                if row["record_type"] != "D":
                    continue

                route_code = int(row["route_code"])
                if route_code not in routes:
                    continue

                if row["entry_type"] == "A":
                    routes[route_code]["all_included_crs"].append(row["crs_code"])
                elif row["entry_type"] == "I":
                    routes[route_code]["any_included_crs"].append(row["crs_code"])
                elif row["entry_type"] == "E":
                    routes[route_code]["excluded_crs"].append(row["crs_code"])
                elif row["entry_type"] == "T":
                    routes[route_code]["included_tocs"].append(row["toc_id"])
                elif row["entry_type"] == "X":
                    routes[route_code]["excluded_tocs"].append(row["toc_id"])
                elif row["entry_type"] == "L":
                    routes[route_code]["included_modes"].append(row["mode_code"])
                elif row["entry_type"] == "N":
                    routes[route_code]["excluded_modes"].append(row["mode_code"])

        with storage.open("routes.json", "w") as f:
            json.dump(routes, f)

        r = niquests.get("https://internal.nationalrail.co.uk/xml/4.0/ticket-types.xml")
        r.raise_for_status()

        data = xml_parser.from_string(r.text, main.rsp.gen.nre_ticket_v4_0.TicketTypeDescriptionList)

        with storage.open("ticket-types.json", "w") as f:
            type_codes = {}
            for i, t in enumerate(data.ticket_type_description):
                for code in t.ticket_type_code:
                    type_codes[code] = i
            json.dump({
                "type_codes": type_codes,
                "data": serializer.encode(data)
            }, f)

        r = niquests.get("https://internal.nationalrail.co.uk/xml/4.0/ticket-restrictions.xml")
        r.raise_for_status()

        data = xml_parser.from_string(r.text, main.rsp.gen.nre_ticket_restriction_v4_0.TicketRestrictions)

        with storage.open("ticket-restrictions.json", "w") as f:
            type_codes = {}
            for i, t in enumerate(data.ticket_restriction):
                type_codes[t.restriction_code] = i
            json.dump({
                "type_codes": type_codes,
                "data": serializer.encode(data)
            }, f)

        r = niquests.get("https://internal.nationalrail.co.uk/4.0/stations.zip")
        r.raise_for_status()

        stations_zip = zipfile.ZipFile(io.BytesIO(r.content))
        with stations_zip.open("stations.xml") as f:
            data = xml_parser.from_bytes(f.read(), main.rsp.gen.nre_station_v4_0.StationList)

            with storage.open("stations.json", "w") as f:
                nlc = {}
                crs = {}
                for i, t in enumerate(data.station):
                    crs[t.crs_code] = i
                    nlc[t.alternative_identifiers.national_location_code] = i
                json.dump({
                    "nlc": nlc,
                    "crs": crs,
                    "data": serializer.encode(data)
                }, f)