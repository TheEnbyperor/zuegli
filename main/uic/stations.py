import typing
import django.core.files.storage
import json
import gtfs.models

STATIONS = None
UIC_STATIONS = None
FINNISH_STATIONS = None
SZ_STATIONS = None

def get_stations_list() -> typing.Dict[str, typing.Any]:
    global STATIONS

    if STATIONS:
        return STATIONS

    uic_storage = django.core.files.storage.storages["uic-data"]
    with uic_storage.open("stations.json", "r") as f:
        STATIONS = json.load(f)

    return STATIONS

def get_uic_stations_list() -> typing.Dict[str, typing.Any]:
    global UIC_STATIONS

    if UIC_STATIONS:
        return UIC_STATIONS

    uic_storage = django.core.files.storage.storages["uic-data"]
    with uic_storage.open("uic-stations.json", "r") as f:
        UIC_STATIONS = json.load(f)

    return UIC_STATIONS

def get_finnish_stations_list() -> typing.Dict[str, typing.Any]:
    global FINNISH_STATIONS

    if FINNISH_STATIONS:
        return FINNISH_STATIONS

    uic_storage = django.core.files.storage.storages["uic-data"]
    with uic_storage.open("finnish-stations.json", "r") as f:
        FINNISH_STATIONS = json.load(f)

    return FINNISH_STATIONS

def get_sz_stations_list() -> typing.Dict[str, typing.Any]:
    global SZ_STATIONS

    if SZ_STATIONS:
        return SZ_STATIONS

    uic_storage = django.core.files.storage.storages["uic-data"]
    with uic_storage.open("sz-stations.json", "r") as f:
        SZ_STATIONS = json.load(f)

    return SZ_STATIONS


def get_station_by_uic(code) -> typing.Optional[dict]:
    code = str(code)
    if code in UIC_CODE_REMAPPING:
        code = UIC_CODE_REMAPPING[code]

    if i := get_stations_list()["uic_codes"].get(code):
        return get_stations_list()["stations"][i]
    if i := get_uic_stations_list()["uic_codes"].get(code):
        return get_uic_stations_list()["stations"][i]
    return None


def get_station_by_db(code) -> typing.Optional[dict]:
    if i := get_stations_list()["db_ids"].get(str(code)):
        return get_stations_list()["stations"][i]
    return None


def get_station_by_uic_sncf(code) -> typing.Optional[dict]:
    if i := get_stations_list()["uic_sncf_codes"].get(str(code)):
        return get_stations_list()["stations"][i]
    return None


def get_station_by_sncf(code) -> typing.Optional[dict]:
    if i := get_stations_list()["sncf_ids"].get(str(code)):
        return get_stations_list()["stations"][i]
    return None


def get_station_by_benerail(code) -> typing.Optional[dict]:
    if i := get_stations_list()["benerail_ids"].get(str(code)):
        return get_stations_list()["stations"][i]
    return None


def get_station_by_finland(code) -> typing.Optional[dict]:
    code = str(code)
    i = get_finnish_stations_list()["station_codes"].get(code)
    if not i:
        i = get_finnish_stations_list()["station_codes"].get(code.replace("?", "Ä"))
    if not i:
        i = get_finnish_stations_list()["station_codes"].get(code.replace("?", "Ö"))
    if i:
        station = get_finnish_stations_list()["stations"][i]
        return get_station_by_uic(1000000 + station["stationUICCode"])
    return None


def get_station_by_sz(code) -> typing.Optional[dict]:
    code = str(code)
    if uic_code := get_sz_stations_list().get(code):
        return get_station_by_uic(uic_code)
    return None


def get_station_by_mav(code) -> typing.Optional[dict]:
    code = str(code)
    if s := gtfs.models.Stop.objects.filter(
        feed_id="mav",
        stop_id=code,
    ).first():
        return {
            "name": s.name,
            "latitude": s.lat,
            "longitude": s.long,
            "country": "HU"
        }
    return None

# DB is stupid and uses the wrong codes sometimes
UIC_CODE_REMAPPING = {
    "8033452": "8065969",
    "8014558": "8019763",
    "8013414": "8014893",
    "8021207": "8018116",
    "8019039": "8019041",
    "8013578": "8017057",
    "8013632": "8011909",
    "8020422": "8015223",
    "8013051": "8013874",
    "8013228": "8014746",
    "8010218": "8017192",
    "8014431": "8500090",
    "8021097": "8012862",
    "8013733": "8017775",
    "8010359": "8018238",
    "8019404": "8019403",
    "8020069": "8102184",
    "8010144": "8013615",
    "8010016": "8024712",
    "8011311": "8020909",
    "8010375": "8019783",
    "8028469": "8044401",
    "8022610": "8010296",
    "8029318": "8020382",
    "8022804": "8011963",
    "8019023": "8015651",
    "8003137": "8065969",
    "8088811": "8013331",
    "8001048": "8013012",
    "8000879": "8021156",
    "8020060": "8101114",
    "8004154": "8020282",
    "8000297": "8018238",
    "8016563": "8016392",
    "8028474": "8044402",
    "8026002": "8014969",
    "8029066": "8013838",
    "8001564": "8050642",
    "8000152": "8013552",
    "8000013": "8002071",
    "8021091": "8016164",
    "8029309": "8018814",
    "8001495": "8015253",
    "8001631": "8016559",
    "8008016": "8019612",
    "8002253": "8016964",
    "8014489": "8503424",
}