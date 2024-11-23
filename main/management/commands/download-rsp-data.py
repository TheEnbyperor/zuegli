import zipfile
import io
from django.core.management.base import BaseCommand
import django.core.files.storage
import niquests
import xsdata.formats.dataclass.parsers
import xsdata.formats.dataclass.parsers.config
import xsdata.formats.dataclass.serializers
import xsdata.models.datatype
import json
import main.rsp.gen.nre_ticket_v4_0

xml_parser = xsdata.formats.dataclass.parsers.XmlParser(config=xsdata.formats.dataclass.parsers.config.ParserConfig(
    fail_on_unknown_properties=False,
))
serializer = xsdata.formats.dataclass.serializers.JsonSerializer()

class Command(BaseCommand):
    help = "Download RDG RSP data"

    def handle(self, *args, **options):
        storage = django.core.files.storage.storages["rsp-data"]

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
                for i, t in enumerate(data.station):
                    nlc[t.alternative_identifiers.national_location_code] = i
                json.dump({
                    "nlc": nlc,
                    "data": serializer.encode(data)
                }, f)