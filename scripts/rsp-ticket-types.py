import pathlib
import xsdata.formats.dataclass.parsers
import xsdata.models.datatype
import json
import sys
import django

ROOT_DIR = pathlib.Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
django.setup()

from main.rsp.gen import ticket_types_ref_data_v1_2

xml_parser = xsdata.formats.dataclass.parsers.XmlParser()


def main():
    with open(ROOT_DIR / "data" / "TicketTypesRefData_v1.2.xml") as f:
        d = f.read()

    data = xml_parser.from_string(d, ticket_types_ref_data_v1_2.TicketTypesReferenceData)
    out = {}
    for fare in data.ticket_type:
        if fare.ojpdisplay_name:
            out[fare.code] = {
                "name": fare.ojpdisplay_name,
            }
        elif fare.rspdisplay_name:
            out[fare.code] = {
                "name": fare.rspdisplay_name,
            }
        elif fare.name:
            out[fare.code] = {
                "name": fare.name,
            }

        if fare.ojpadvice_message:
            out[fare.code]["advise"] = fare.ojpadvice_message
        elif fare.rspadvice:
            out[fare.code]["advise"] = fare.rspadvice

    with open(ROOT_DIR / "rsp-data" / "ticket-types.json", "w") as f:
        json.dump(out, f)


if __name__ == "__main__":
    main()