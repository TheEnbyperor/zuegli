import datetime
import decimal
import math
import pytz
import typing
import uuid
import iso3166
from django import template
from .. import uic, vdv, swisspass

register = template.Library()

@register.filter(name="as_hex")
def as_hex(value: typing.Union[bytes, int]) -> str:
    if isinstance(value, int):
        l = (math.ceil(math.log2(value)) + 7) // 8
        value = value.to_bytes(l, "big")
    return ":".join(f"{b:02X}" for b in value)

@register.filter(name="to_date")
def to_date(value):
    return datetime.datetime.fromisoformat(value)

@register.filter(name="undo_iso_8859")
def undo_iso_8859(value: str):
    try:
        return value.encode("iso-8859-1").decode("utf-8")
    except ValueError:
        return value

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
        elif code_type == "uic_sncf":
            return uic.stations.get_station_by_uic_sncf(value)
        elif code_type == "benerail":
            return uic.stations.get_station_by_benerail(value)
        elif code_type == "finland":
            return uic.stations.get_station_by_finland(value)
        elif code_type == "sz":
            return uic.stations.get_station_by_sz(value)
        elif code_type == "mav":
            return uic.stations.get_station_by_mav(value)
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

    return None

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

    return None

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
        tz = datetime.timezone(-datetime.timedelta(minutes=15 * value["validFromUTCOffset"]))
        issuing_time = issuing_time.replace(tzinfo=tz)
    elif value.get("productOwnerNum", None) == 9901:
        issuing_time = pytz.timezone("Europe/Berlin").localize(issuing_time)
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
    valid_from += datetime.timedelta(days=value["validUntilDay"])
    if "validUntilTime" in value:
        valid_from = valid_from.replace(hour=0, minute=0, second=59)
        valid_from += datetime.timedelta(minutes=value["validUntilTime"])
    else:
        valid_from = valid_from.replace(hour=23, minute=59, second=59)
    if "validUntilUTCOffset" in value:
        tz = datetime.timezone(-datetime.timedelta(minutes=15 * value["validUntilUTCOffset"]))
        valid_from = valid_from.replace(tzinfo=tz)
    elif "validFromUTCOffset" in value:
        tz = datetime.timezone(-datetime.timedelta(minutes=15 * value["validFromUTCOffset"]))
        valid_from = valid_from.replace(tzinfo=tz)
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
        tz = datetime.timezone(-datetime.timedelta(minutes=15 * value["departureUTCOffset"]))
        travel_time = travel_time.replace(tzinfo=tz)
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
        tz = datetime.timezone(-datetime.timedelta(minutes=15 * value["arrivalUTCOffset"]))
        travel_time = travel_time.replace(tzinfo=tz)
    return travel_time

@register.filter(name="rics_delay_departure_time")
def rics_delay_departure_time(value):
    if "departureYear" not in value:
        return None
    departure_time = datetime.datetime(value["departureYear"], 1, 1, 0, 0, 0)
    departure_time += datetime.timedelta(days=value["departureDay"]-1, minutes=value.get("departureTime", 0))
    if "departureUTCOffset" in value:
        tz = datetime.timezone(-datetime.timedelta(minutes=15 * value["departureUTCOffset"]))
        departure_time = departure_time.replace(tzinfo=tz)
    return departure_time


@register.filter(name="nuts_region_name")
def nuts_region_name(value):
    if region := uic.nuts.get_nuts_by_code(value):
        return region["NUTS_NAME"]
    return None


@register.filter(name="via_as_graphviz")
def via_as_graphviz(value):
    if value.lower().startswith("via:") or value.lower().startswith("via "):
        via = uic.parse_via.parse_via(value)
        return uuid.uuid4(), via.to_graph()
    return None


@register.filter(name="flex_via_as_graphviz")
def flex_via_as_graphviz(value):
    via = uic.parse_via.FlexVia.parse(value)
    return uuid.uuid4(), via.to_graph()


@register.filter(name="sz_as_graphviz")
def sz_as_graphviz(value):
    via = uic.parse_via.get_route_by_sz(value)
    return uuid.uuid4(), via


@register.filter(name="vdv_org_id")
def vdv_org_id(value):
    if isinstance(value, int):
        return vdv.ticket.map_org_id(value, True)
    elif value.startswith("VDV"):
        value = value[3:]
        if value.startswith("KA"):
            value = value[2:]
        try:
            org_id = int(value)
        except ValueError:
            return None
        return vdv.ticket.map_org_id(org_id, True)
    else:
        return None


@register.filter(name="vdv_product_id")
def vdv_product_id(value, org_id: str):
    if org_id.startswith("VDV"):
        org_id = org_id[3:]
        if org_id.startswith("KA"):
            org_id = org_id[2:]
        try:
            org_id = int(org_id)
        except ValueError:
            return None
        return vdv.ticket.product_name(org_id, value, True)
    else:
        return None


@register.filter(name="swisspass_org_id")
def swisspass_org_id(value):
    return swisspass.org_id.get_org(value)


@register.filter(name="validity_zone_names")
def validity_zone_names(value):
    if value.get("carrierIA5", "").startswith("VDV"):
        org_id = int(value["carrierIA5"][3:])
        return vdv.ticket.SpatialValidity.map_names(org_id, value["zoneId"])
    else:
        out = []
        for zone_id in value["zoneId"]:
            out.append(f"Unknown zone: {zone_id}")
        return out

@register.filter(name="uic_price")
def uic_price(value: int, issuing_detail: dict):
    currency_code = issuing_detail.get("currency", "")
    fraction = 10 ** issuing_detail.get("currencyFract", 0)
    value = decimal.Decimal(value) / decimal.Decimal(fraction)

    return f"{value:.02f} {currency_code}"


@register.filter(name="dosipas_timestamp")
def dosipas_timestamp(value: dict):
    this_year = datetime.datetime.now().year
    out = datetime.datetime(this_year, 1, 1)
    out += datetime.timedelta(days=value["day"] - 1)
    out += datetime.timedelta(seconds=value["time"])
    return pytz.utc.localize(out)


@register.filter(name="uic_geo")
def uic_geo(value: dict):
    long = decimal.Decimal(value["longitude"])
    lat = decimal.Decimal(value["latitude"])

    if value["geoUnit"] == "deciDegree":
        pass
    elif value["geoUnit"] == "centiDegree":
        long /= 100
        lat /= 100
    elif value["geoUnit"] == "milliDegree":
        long /= 1_000
        lat /= 1_000
    elif value["geoUnit"] == "tenthmilliDegree":
        long /= 10_000
        lat /= 10_000
    elif value["geoUnit"] == "microDegree":
        long /= 1_000_000
        lat /= 1_000_000

    if value["hemisphereLongitude"] == "west":
        long = -long
    if value["hemisphereLatitude"] == "south":
        lat = -lat

    return uic.util.Coordinate(
        coordinate_system=value["coordinateSystem"],
        longitude=long,
        latitude=lat
    )

@register.filter(name="uic_points_js")
def uic_points_js(value: dict):
    start_long = decimal.Decimal(value["firstEdge"]["longitude"])
    start_lat = decimal.Decimal(value["firstEdge"]["latitude"])

    if value["firstEdge"]["geoUnit"] == "deciDegree":
        divider = 1
    elif value["firstEdge"]["geoUnit"] == "centiDegree":
        divider = 100
    elif value["firstEdge"]["geoUnit"] == "milliDegree":
        divider = 1_000
    elif value["firstEdge"]["geoUnit"] == "tenthmilliDegree":
        divider = 10_000
    elif value["firstEdge"]["geoUnit"] == "microDegree":
        divider = 1_000_000
    else:
        return

    if value["firstEdge"]["hemisphereLongitude"] == "west":
        start_long = -start_long
    if value["firstEdge"]["hemisphereLatitude"] == "south":
        start_lat = -start_lat

    edges = [(start_long / divider, start_lat / divider)]
    for e in value["edges"]:
        edges.append((
            (start_long - decimal.Decimal(e["longitude"])) / divider,
            (start_lat - decimal.Decimal(e["latitude"])) / divider,
        ))

    out = "["
    for e in edges:
        out += f"[{e[1]},{e[0]}],"
    out += "]"
    return out


@register.filter(name="sncf_ext_parse")
def sncf_ext_parse(value: bytes):
    return uic.sncf.SNCFTransport.parse(1, value)


@register.filter(name="en1545_transport_type")
def en1545_transport_type(value: int):
    if value == 1:
        return "Urban bus"
    elif value == 2:
        return "Interurban bus"
    elif value == 3:
        return "Metro"
    elif value == 4:
        return "Tram"
    elif value == 5:
        return "S-Bahn"
    elif value == 6:
        return "Ferry"
    elif value == 7:
        return "Toll-road"
    elif value == 8:
        return "Parking"
    elif value == 9:
        return "Taxi"
    elif value == 10:
        return "High Speed Train"
    elif value == 11:
        return "Rural bus"
    elif value == 12:
        return "Regional Express"
    elif value == 13:
        return "Para-transit"
    elif value == 14:
        return "Self driving vehicle"
    elif value == 15:
        return "Coach"
    elif value == 16:
        return "Locomotive"
    elif value == 17:
        return "Powered motor vehicle"
    elif value == 18:
        return "Trailer"
    elif value == 19:
        return "Regioahn"
    elif value == 20:
        return "InterCity"
    elif value == 21:
        return "Furnicular"
    else:
        return f"Unknown - {value}"


def afnor_network_id(value: int):
    afnor_ids = uic.sncf.get_afnor_ids()
    country = value // 1000
    network = value % 1000
    country_name = iso3166.countries_by_numeric.get(str(country)).name
    if network == 999:
        network_name = "Whole country"
    elif 991 <= network <= 998:
        network_name = "Test"
    elif country == 250:
        if region_name := afnor_ids["region"].get(network):
            network_name = f"Region {region_name}"
        elif department_name := afnor_ids["department"].get(network):
            network_name = f"Département {department_name}"
        elif authority := afnor_ids["authority"].get(network):
            network_name = f"{authority['name']} - {authority['org']} ({authority['siren']})"
        else:
            network_name = "Unknown"
    else:
        network_name = None
    return {
        "country": country_name,
        "network_id": network,
        "network_name": network_name,
    }

@register.filter(name="intercode_network_id")
def intercode_network_id(value: bytes):
    return afnor_network_id(vdv.util.un_bcd(value))

@register.filter(name="dbr_network_id")
def dbr_network_id(value: int):
    return afnor_network_id(value)

@register.filter(name="intercode_retail_generator_id")
def intercode_retail_generator_id(value: int):
    intercode_data = uic.sncf.get_intercode_data()
    return intercode_data["retail_generator_id"].get(str(value))


@register.filter(name="intercode_retail_server_id")
def intercode_retail_server_id(value: int):
    intercode_data = uic.sncf.get_intercode_data()
    return intercode_data["retail_server_id"].get(str(value))


@register.filter(name="intercode_retailer_id")
def intercode_retailer_id(value: int):
    intercode_data = uic.sncf.get_intercode_data()
    return intercode_data["retailer_id"].get(str(value))


@register.filter(name="format_evn")
def format_evn(value: int):
    value = f"{value}:012"
    return f"{value[0:2]} {value[2:4]} {value[4:8]} {value[8:11]} - {value[11:12]}"
