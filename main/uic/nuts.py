import csv
import pathlib

NUTS_DATA = None
ROOT_DIR = pathlib.Path(__file__).parent

def get_nuts_data():
    global NUTS_DATA

    if NUTS_DATA:
        return NUTS_DATA

    NUTS_DATA = {
        "rows": [],
        "codes": {}
    }
    with open(ROOT_DIR / "data" / "NUTS_AT_2024.csv") as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            NUTS_DATA["rows"].append(r)
            NUTS_DATA["codes"][r["NUTS_ID"]] = i

    return NUTS_DATA


def get_nuts_by_code(code: str):
    data = get_nuts_data()
    if code in data["codes"]:
        return data["rows"][data["codes"][code]]