import pathlib
import json
from ..uic import stations
from .. import models

VRS_TARIFGEBIETE = None
VBB_TARIFBEREICHE = None
DATA_DIR = pathlib.Path(__file__).parent / 'data'

def get_vrs_tarifgebiete_list():
    global VRS_TARIFGEBIETE

    if VRS_TARIFGEBIETE:
        return VRS_TARIFGEBIETE

    with open(DATA_DIR / "vrs-tarifgebiete.json") as f:
        VRS_TARIFGEBIETE = json.load(f)

    return VRS_TARIFGEBIETE

def get_vbb_tarifbereiche_list():
    # https://sbahn.berlin/fileadmin/user_upload/Tickets/Tarifgebiet_Berlin-Brandenburg/Tarifbroschueren/vbbtarif-zielorte.pdf
    global VBB_TARIFBEREICHE

    if VBB_TARIFBEREICHE:
        return VBB_TARIFBEREICHE

    with open(DATA_DIR / "vbb-tarifbereiche.json") as f:
        VBB_TARIFBEREICHE = json.load(f)

    return VBB_TARIFBEREICHE


def get_db_station_name(code: int):
    if station := stations.get_station_by_db(code):
        return station["name"]
    else:
        return None


def vrs_tariff(code: int):
    if name := get_vrs_tarifgebiete_list().get(str(code), None):
        return name
    else:
        return None

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
    else:
        return None


def vbb_tariff(code: int):
    if 9000000 <= code <= 9999999:
        code = str(code)
        code = f"900{code[1:]}"
        if station := models.ZHVStop.objects.filter(dhid_raw_id=code, authority="VBB").first():
            return f"{station.name}, {station.municipality}"
        else:
            return None
    elif name := get_vbb_tarifbereiche_list().get(str(code), None):
        return name
    else:
        return None

def saarvv_tariff(code: int):
    if code < 1000:
        return f"Waben {code}"
    else:
        return None


SPACIAL_VALIDITY = {
    36: {
        100: "Biedenkopf",
        200: "Wetter",
        300: "Kirchhain",
        400: "Gladenbach",
        500: "Marburg",
        700: "Homberg (Ohm)",
        800: "Alsfeld",
        900: "Mücke",
        1000: "Lauterbach",
        1100: "Schlitz",
        1200: "Grebenhain",
        1300: "Schotten",
        1400: "Lich",
        1500: "Gießen",
        1600: "Hünfeld",
        1700: "Tann",
        1800: "Gersfeld",
        1900: "Neuhof",
        2000: "Fulda",
        2100: "Großenlüder",
        2200: "Butzbach",
        2300: "Nidda",
        2400: "Gedern",
        2500: "Friedberg",
        2600: "Bad Vilbel",
        2700: "Büdingen",
        2900: "Maintal",
        3000: "Hanau",
        3100: "Gelnhausen",
        3200: "Birstein",
        3300: "Bad Orb",
        3400: "Schlüchtern",
        3500: "Langen",
        3600: "Offenbach",
        3700: "Groß-Gerau",
        3800: "Riedstadt",
        3900: "Seeheim-Jugenheim",
        4000: "Darmstadt",
        4100: "Dieburg",
        4200: "Erbach",
        4300: "Bad König",
        4400: "Beerfelden",
        5000: "Frankfurt ohne Flughafen",
        5090: "Frankfurt Flughafen",
        5100: "Bad Homburg",
        5200: "Usingen",
        5300: "Braunfels",
        5400: "Driedorf",
        5500: "Wetzlar",
        5600: "Bischoffen",
        5700: "Herborn",
        5800: "Dillenburg",
        5900: "Weilburg",
        6000: "Limburg",
        6100: "Bad Camberg",
        6200: "Idstein",
        6300: "Rüdesheim",
        6400: "Bad Schwalbach",
        6500: "Wiesbaden/Mainz",
        6600: "Hotheim am Taunus",
    },
    70: vrr_tariff,
    102: vrs_tariff,
    3000: {
        1: "Deutschlandweit",
    },
    5000: {
        1: "Deutschlandweit",
        3: "Bayern",
        768: "Bayern",
        3584: "Sachsen-Ticket",
        4096: "Schleswig-Holstein-Ticket",
    },
    6100: vbb_tariff,
    6212: {
        904001: "eezy.nrw"
    },
    6262: get_db_station_name,
    6292: {
        8: "Zone 12",
        16: "Zone 11",
        32: "Zone 10",
        64: "Zone 9",
        128: "Zone M",
        256: "Zone 7",
        512: "Zone 6",
        1024: "Zone 5",
        2048: "Zone 4",
        4096: "Zone 3",
        8192: "Zone 2",
        16384: "Zone 1",
        32768: "Zone 8",
    },
    6310: saarvv_tariff,
    6538: {
        101: "Zone 101 - Koblenz City"
    }
}