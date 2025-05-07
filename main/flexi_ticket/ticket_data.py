import typing
import django.core.files.storage
import json

BRANDS = {}


def get_brand_data(brand: str):
    global BRANDS

    if brand in BRANDS:
        return BRANDS[brand]

    rsp_storage = django.core.files.storage.storages["ft-data"]
    with rsp_storage.open(f"{brand}.json", "r") as f:
        BRANDS[brand] = json.loads(f.read())

    return BRANDS[brand]


def get_station(station_id: str, brand: str) -> typing.Optional[dict]:
    brand_data = get_brand_data(brand)

    return brand_data["stations"].get(str(station_id))


def get_ticket_product(product_id: str, brand: str) -> typing.Optional[dict]:
    brand_data = get_brand_data(brand)

    return brand_data["products"].get(product_id)