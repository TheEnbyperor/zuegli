import csv
import typing
import django.core.files.storage
import json

AIRLINES = None
AIRPORTS = None

def get_airlines_list() -> typing.Dict[str, typing.Any]:
    global AIRLINES

    if AIRLINES:
        return AIRLINES

    iata_storage = django.core.files.storage.storages["iata-data"]
    with iata_storage.open("airlines.txt", "r") as f:
        r = csv.DictReader(f, delimiter="\t")
        airlines = list(r)

    AIRLINES = {
        "iata_codes": {},
        "icao_codes": {},
        "prefix_codes": {},
        "airlines": airlines,
    }
    for i, airline in enumerate(airlines):
        if airline["IATA_Code"]:
            AIRLINES["iata_codes"][airline["IATA_Code"]] = i
        if airline["ICAO_Code"]:
            AIRLINES["icao_codes"][airline["ICAO_Code"]] = i
        if airline["Prefix_Code"]:
            AIRLINES["prefix_codes"][int(airline["Prefix_Code"])] = i

    return AIRLINES

def get_airports_list() -> typing.Dict[str, typing.Any]:
    global AIRPORTS

    if AIRPORTS:
        return AIRPORTS

    iata_storage = django.core.files.storage.storages["iata-data"]
    with iata_storage.open("airports.json", "r") as f:
        AIRPORTS = json.loads(f.read())

    return AIRPORTS


def get_iata_airline(code: str) -> typing.Optional[dict]:
    data = get_airlines_list()
    if i := data["iata_codes"].get(code):
        return data["airlines"][i]


def get_icao_airline(code: str) -> typing.Optional[dict]:
    data = get_airlines_list()
    if i := data["icao_codes"].get(code):
        return data["airlines"][i]


def get_prefix_code_airline(code: int) -> typing.Optional[dict]:
    data = get_airlines_list()
    if i := data["prefix_codes"].get(code):
        return data["airlines"][i]


def get_iata_airport(code: str) -> typing.Optional[dict]:
    data = get_airports_list()
    if i := data["iata_codes"].get(code):
        return data["airports"][i]
