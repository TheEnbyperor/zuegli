import datetime
import pytz
import typing
import uuid
import iso3166
from django import template
from .. import uic, vdv

register = template.Library()

@register.filter(name="rics")
def get_rics_code(value):
    if not value:
        return None
    return uic.rics.get_rics(int(value))

@register.filter(name="get_station")
def get_station(value, code_type):
    if not value:
        return None

    if isinstance(code_type, str):
        if code_type == "db":
            return uic.stations.get_station_by_db(value)
        elif code_type == "sncf":
            return uic.stations.get_station_by_sncf(value)
        elif code_type == "benerail":
            return uic.stations.get_station_by_benerail(value)
        elif code_type == "uic":
            return uic.stations.get_station_by_uic(value)
    elif isinstance(code_type, dict):
        if code_type.get("stationCodeTable") == "stationUIC":
            return uic.stations.get_station_by_uic(value)
        elif code_type.get("stationCodeTable") == "stationUICReservation":
            return
        elif code_type.get("stationCodeTable") == "localCarrierStationCodeTable":
            if code_type.get("productOwnerNum") == 1154:
                if s := uic.stations.get_station_by_uic(value):
                    return s
                if s := uic.stations.get_station_by_db(value):
                    return s

@register.filter(name="iso3166")
def get_country(value):
    return iso3166.countries.get(value).name

@register.filter(name="uic_country")
def get_country_uic(value):
    return uic.countries.get_country_name_by_uic(value)

@register.filter(name="rics_already_newlined")
def ics_already_newlined(value):
    return "\n" in value

@register.filter(name="rics_traveler_dob")
def rics_traveler_dob(value):
    if "yearOfBirth" in value or "monthOfBirth" in value or "dayOfBirthInMonth" in value or "dayOfBirth" in value:
        if "dayOfBirth" in value:
            birthdate = datetime.date(value.get("yearOfBirth", 0), 1, 1)
            birthdate += datetime.timedelta(days=value["dayOfBirth"]-1)
            return birthdate
        else:
            return datetime.date(
                value.get("yearOfBirth", 0),
                value.get("monthOfBirth", 1),
                value.get("dayOfBirthInMonth", 1),
            )

@register.filter(name="rics_unicode")
def rics_unicode(value):
    return value.decode("utf-8", "replace")

@register.filter(name="rics_valid_from")
def rics_valid_from(value, issuing_time: typing.Optional[datetime.datetime]=None):
    if issuing_time:
        issuing_time = datetime.datetime.combine(issuing_time.date(), datetime.time.min)
        issuing_time += datetime.timedelta(days=value["validFromDay"], minutes=value.get("validFromTime", 0))
    else:
        if "validFromYear" not in value:
            return
        issuing_time = datetime.datetime(value["validFromYear"], 1, 1, 0, 0, 0)
        issuing_time += datetime.timedelta(days=value["validFromDay"]-1, minutes=value.get("validFromTime", 0))
    if "validFromUTCOffset" in value:
        issuing_time += datetime.timedelta(minutes=15 * value["validFromUTCOffset"])
        issuing_time = issuing_time.replace(tzinfo=pytz.utc)
    return issuing_time

@register.filter(name="rics_valid_from_date")
def rics_valid_from_date(value):
    if "validFromYear" not in value:
        return
    valid_time = datetime.datetime(value["validFromYear"], 1, 1, 0, 0, 0)
    valid_time += datetime.timedelta(days=value["validFromDay"]-1)
    return pytz.utc.localize(valid_time)

@register.filter(name="rics_valid_until")
def rics_valid_until(value, issuing_time: typing.Optional[datetime.datetime]=None):
    valid_from = rics_valid_from(value, issuing_time)
    if "validUntilYear" in value:
        valid_from = valid_from.replace(
            year=valid_from.year + value["validUntilYear"],
        )
    valid_from += datetime.timedelta(days=value["validUntilDay"], minutes=value.get("validUntilTime", 0))
    if "validUntilUTCOffset" in value:
        valid_from += datetime.timedelta(minutes=15 * value["validUntilUTCOffset"])
        valid_from = valid_from.replace(tzinfo=pytz.utc)
    elif "validFromUTCOffset" in value:
        valid_from += datetime.timedelta(minutes=15 * value["validFromUTCOffset"])
        valid_from = valid_from.replace(tzinfo=pytz.utc)
    return valid_from


@register.filter(name="rics_valid_until_date")
def rics_valid_until_date(value):
    valid_from = rics_valid_from_date(value).replace(day=1, month=1)
    if "validUntilYear" in value:
        valid_from = valid_from.replace(
            year=valid_from.year + value["validUntilYear"],
        )
    valid_from += datetime.timedelta(days=value["validUntilDay"]-1)
    valid_from = pytz.utc.localize(datetime.datetime.combine(valid_from.date(), datetime.time.max))
    return valid_from


@register.filter(name="rics_departure_time")
def rics_departure_time(value, issuing_time: datetime.datetime):
    if "departureDate" in value:
        travel_time = issuing_time + datetime.timedelta(days=value["departureDate"])
    else:
        travel_time = issuing_time + datetime.timedelta(days=value["travelDate"])
    travel_time = travel_time.replace(hour=0, minute=0, second=0, microsecond=0)
    travel_time += datetime.timedelta(minutes=value["departureTime"])
    if "departureUTCOffset" in value:
        travel_time += datetime.timedelta(minutes=15 * value["departureUTCOffset"])
        travel_time = travel_time.replace(tzinfo=pytz.utc)
    return travel_time


@register.filter(name="rics_arrival_time")
def rics_arrival_time(value, issuing_time: datetime.datetime):
    if "departureDate" in value:
        travel_time = issuing_time + datetime.timedelta(days=value["departureDate"])
    else:
        travel_time = issuing_time + datetime.timedelta(days=value["travelDate"])
    if "arrivalDate" in value:
        travel_time += datetime.timedelta(days=value["arrivalDate"])
    travel_time = travel_time.replace(hour=0, minute=0, second=0, microsecond=0)
    travel_time += datetime.timedelta(minutes=value["arrivalTime"])
    if "arrivalUTCOffset" in value:
        travel_time += datetime.timedelta(minutes=15 * value["arrivalUTCOffset"])
        travel_time = travel_time.replace(tzinfo=pytz.utc)
    return travel_time


@register.filter(name="nuts_region_name")
def nuts_region_name(value):
    if region := uic.nuts.get_nuts_by_code(value):
        return region["NUTS_NAME"]


@register.filter(name="via_as_graphviz")
def via_as_graphviz(value):
    if value.lower().startswith("via:"):
        via = uic.parse_via.parse_via(value)
        return uuid.uuid4(), via.to_graph()


@register.filter(name="vdv_org_id")
def vdv_org_id(value):
    if value.startswith("VDV"):
        org_id = int(value[3:])
        return vdv.ticket.map_org_id(org_id, True)


@register.filter(name="vdv_product_id")
def vdv_product_id(value, org_id: str):
    if org_id.startswith("VDV"):
        org_id = int(org_id[3:])
        return vdv.ticket.product_name(org_id, value, True)


@register.filter(name="validity_zone_names")
def validity_zone_names(value):
    if value.get("carrierIA5").startswith("VDV"):
        org_id = int(value["carrierIA5"][3:])
        return vdv.ticket.SpacialValidity.map_names(org_id, value["zoneId"])
    else:
        out = []
        for zone_id in value["zoneId"]:
            out.append(f"Unknown zone: {zone_id}")
        return out
