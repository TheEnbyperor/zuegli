import typing
import django.core.files.storage
import json

CORPUS = None
NLC = None

def get_corpus_data() -> typing.Dict[str, typing.Any]:
    global CORPUS

    if CORPUS:
        return CORPUS

    rsp_storage = django.core.files.storage.storages["rsp-data"]
    CORPUS = {}
    with rsp_storage.open("CORPUSExtract.json", "r") as f:
        CORPUS["locations"] = json.load(f)["TIPLOCDATA"]

    CORPUS["NLC"] = {}
    for i, l in enumerate(CORPUS["locations"]):
        CORPUS["NLC"][str(l["NLC"])] = i

    return CORPUS

def get_nlc_data() -> typing.Dict[str, typing.Any]:
    global NLC

    if NLC:
        return NLC

    rsp_storage = django.core.files.storage.storages["rsp-data"]
    with rsp_storage.open("nlc.json", "r") as f:
        NLC = json.load(f)

    return NLC


def get_station_by_nlc(code: str) -> typing.Optional[dict]:
    if len(code) <= 4:
        lcode = f"{code}00"
    else:
        lcode = code

    if i := get_nlc_data().get(code):
        if c := get_corpus_data()["NLC"].get(lcode):
            l = get_corpus_data()["locations"][c]
            if "3ALPHA" in l:
                i["3ALPHA"] = l["3ALPHA"]
        return i

    if i := get_corpus_data()["NLC"].get(lcode):
        return get_corpus_data()["locations"][i]

    return None
