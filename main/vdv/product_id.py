import pathlib
import typing
import json

PRODUCT_IDS = None
DATA_DIR = pathlib.Path(__file__).parent / 'data'

def get_product_id_list() -> typing.Dict[typing.Tuple[int, int], str]:
    global PRODUCT_IDS

    if PRODUCT_IDS:
        return PRODUCT_IDS

    PRODUCT_IDS = {}
    for file in (DATA_DIR / "products").glob('*.json'):
        with open(file, "r") as f:
            data = json.load(f)
            for i in data["textmap"]:
                if "_" not in i["key"]:
                    continue
                org_id, product_id = i["key"].split("_", 1)
                org_id = int(org_id)
                product_id = int(product_id)
                PRODUCT_IDS[(org_id, product_id)] = i["text"]

    return PRODUCT_IDS