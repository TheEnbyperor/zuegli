import pathlib
import xsdata.formats.dataclass.parsers
import xsdata.models.datatype
import json
import sys
import django

ROOT_DIR = pathlib.Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
django.setup()

from main.rsp.gen import fare_locations_ref_data_v1_3

xml_parser = xsdata.formats.dataclass.parsers.XmlParser()


def main():
    with open(ROOT_DIR / "data" / "FareLocationsRefData_v1.3.xml") as f:
        d = f.read()

    data = xml_parser.from_string(d, fare_locations_ref_data_v1_3.FareLocationsReferenceData)
    out = {}
    for loc in data.fare_location:
        if loc.ojpdisplay_name:
            out[loc.nlc] = {
                "NLCDESC": loc.ojpdisplay_name,
            }
        elif loc.rspdisplay_name:
            out[loc.nlc] = {
                "NLCDESC": loc.rspdisplay_name,
            }
        elif loc.name:
            out[loc.nlc] = {
                "NLCDESC": loc.name
            }

    with open(ROOT_DIR / "rsp-data" / "nlc.json", "w") as f:
        json.dump(out, f)


if __name__ == "__main__":
    main()