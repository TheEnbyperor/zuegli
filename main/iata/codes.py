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
    with iata_storage.open("airlines.json", "r") as f:
        AIRLINES = json.loads(f.read())

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


def get_iata_airport(code: str) -> typing.Optional[dict]:
    data = get_airports_list()
    if i := data["iata_codes"].get(code):
        return data["airports"][i]
