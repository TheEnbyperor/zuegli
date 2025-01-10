import pathlib
import json
from ..uic import stations
from .. import models

VRS_TARIFGEBIETE = None
DATA_DIR = pathlib.Path(__file__).parent / 'data'

def get_vrs_tarifgebiete_list():
    global VRS_TARIFGEBIETE

    if VRS_TARIFGEBIETE:
        return VRS_TARIFGEBIETE

    with open(DATA_DIR / "vrs-tarifgebiete.json") as f:
        VRS_TARIFGEBIETE = json.load(f)

    return VRS_TARIFGEBIETE


def get_db_station_name(code: int):
    if station := stations.get_station_by_db(code):
        return station["name"]


def vrs_tariff(code: int):
    if name := get_vrs_tarifgebiete_list().get(str(code), None):
        return name

def vrr_tariff(code: int):
    if 100000 <= code <= 108999:
        return f"Preisstufe A, 2-Waben in Zeittarif: Waben {code - 100000}"
    elif 109000 <= code <= 109999:
        return f"Kreisweite Gültigkeit: Waben {code - 109000}"
    elif 110000 <= code <= 110999:
        return f"Preisstufe A: Waben {code - 110000}"
    elif 120000 <= code <= 129999:
        return f"Preisstufe B im Zeittarif: Waben {code - 120000}"
    elif 130000 <= code <= 130999:
        return f"Preisstufe C im Zeittarif: Waben {code - 130000}"
    elif 140000 <= code <= 140999 or 150000 <= code <= 150999:
        return f"Preisstufe D: Waben {code - 140000}"
    elif 160000 <= code <= 160999:
        return f"2-Waben im Bartarif: Waben {code - 160000}"
    elif 180000 <= code <= 180999:
        return f"Preisstufe B im Bartarif: Waben {code - 180000}"
    elif 190000 <= code <= 190999:
        return f"Preisstufe C im Bartarif: Waben {code - 190000}"


def vbb_tariff(code: int):
    if 9000000 <= code <= 9999999:
        code = str(code)
        code = f"900{code[1:]}"
        if station := models.ZHVStop.objects.filter(dhid_raw_id=code, authority="VBB").first():
            return f"{station.name}, {station.municipality}"
    elif code == 1200:
        return "Berlin AB"
    elif code == 1201:
        return "Berlin BC"
    elif code == 1202:
        return "Berlin ABC"


SPACIAL_VALIDITY = {
    70: vrr_tariff,
    102: vrs_tariff,
    3000: {
        1: "Deutschlandweit",
    },
    5000: {
        1: "Deutschlandweit",
        3: "Bayern",
        768: "Bayern",
        4096: "Schleswig-Holstein-Ticket",
    },
    6100: vbb_tariff,
    6212: {
        904001: "eezy.nrw"
    },
    6262: get_db_station_name,
}