import typing
import django.core.files.storage
import json
import xsdata.formats.dataclass.parsers
from . import gen

TICKET_TYPES = None
TICKET_RESTRICTIONS = None
STATIONS = None

parser = xsdata.formats.dataclass.parsers.JsonParser()

def get_ticket_types():
    global TICKET_TYPES

    if TICKET_TYPES:
        return TICKET_TYPES

    rsp_storage = django.core.files.storage.storages["rsp-data"]
    with rsp_storage.open("ticket-types.json", "r") as f:
        TICKET_TYPES = json.loads(f.read())

    return TICKET_TYPES

def get_ticket_restrictions():
    global TICKET_RESTRICTIONS

    if TICKET_RESTRICTIONS:
        return TICKET_RESTRICTIONS

    rsp_storage = django.core.files.storage.storages["rsp-data"]
    with rsp_storage.open("ticket-restrictions.json", "r") as f:
        TICKET_RESTRICTIONS = json.loads(f.read())

    return TICKET_RESTRICTIONS

def get_stations():
    global STATIONS

    if STATIONS:
        return STATIONS

    rsp_storage = django.core.files.storage.storages["rsp-data"]
    with rsp_storage.open("stations.json", "r") as f:
        STATIONS = json.loads(f.read())

    return STATIONS


def get_ticket_type(code: str) -> typing.Optional[gen.nre_ticket_v4_0.TicketTypeDescription]:
    ticket_types = get_ticket_types()

    if i := ticket_types["type_codes"].get(code):
        d = ticket_types["data"]["TicketTypeDescription"][i]
        return parser.decode(d, gen.nre_ticket_v4_0.TicketTypeDescription)


def get_ticket_restriction(code: str) -> typing.Optional[gen.nre_ticket_restriction_v4_0.TicketRestriction]:
    ticket_restrictions = get_ticket_restrictions()

    if i := ticket_restrictions["type_codes"].get(code):
        d = ticket_restrictions["data"]["TicketRestriction"][i]
        return parser.decode(d, gen.nre_ticket_restriction_v4_0.TicketRestriction)


def get_station_by_nlc(code: str) -> typing.Optional[gen.nre_station_v4_0.Station]:
    if len(code) <= 4:
        code = f"{code}00"

    stations = get_stations()

    if i := stations["nlc"].get(code):
        d = stations["data"]["Station"][i]
        return parser.decode(d, gen.nre_station_v4_0.Station)
