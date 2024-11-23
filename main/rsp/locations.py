import typing
import django.core.files.storage
import json

LOCATIONS = None

def get_locations_data() -> typing.Dict[str, typing.Any]:
    global LOCATIONS

    if LOCATIONS:
        return LOCATIONS

    rsp_storage = django.core.files.storage.storages["rsp-data"]
    LOCATIONS = {}
    with rsp_storage.open("CORPUSExtract.json", "r") as f:
        LOCATIONS["locations"] = json.load(f)["TIPLOCDATA"]

    LOCATIONS["NLC"] = {}
    for i, l in enumerate(LOCATIONS["locations"]):
        LOCATIONS["NLC"][str(l["NLC"])] = i

    return LOCATIONS


def get_station_by_nlc(code: str) -> typing.Optional[dict]:
    if len(code) <= 4:
        code = f"{code}00"

    if i := get_locations_data()["NLC"].get(code):
        return get_locations_data()["locations"][i]