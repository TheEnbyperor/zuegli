import dataclasses
import datetime
import typing
from ..ssb import util as ssb_util
from . import util
from ..uic import rics

@dataclasses.dataclass
class Ticket:
    version: int
    issuer_rics: int
    return_included: bool
    number_tickets: int
    number_adults: int
    number_children: int
    valid_from: typing.Optional[datetime.date]
    valid_until: typing.Optional[datetime.date]
    corporate_frequent_traveler_id: typing.Optional[int]
    individual_frequent_traveler_id: typing.Optional[int]
    departure_station_number: typing.Optional[int]
    departure_station_name: typing.Optional[str]
    arrival_station_number: typing.Optional[int]
    arrival_station_name: typing.Optional[str]
    departure_time: typing.Optional[datetime.time]
    train_number: int
    reservation_reference: int
    travel_class: str
    coach_number: int
    seat: str
    overbooked: bool
    pnr: str
    ticket_type: int
    specimen: bool

    def issuer(self):
        return rics.get_rics(self.issuer_rics)

    @classmethod
    def parse(cls, data: bytes) -> "Ticket":
        if len(data) != 107:
            raise util.SSB1Exception("Invalid length for an SSB1 barcode")

        d = ssb_util.BitStream(data)

        version = d.read_int(0, 4)
        if version not in (1, 2):
            raise util.SSB1Exception("Not an SSB1 barcode")

        valid_from_day = d.read_int(39, 48)
        valid_until_day = d.read_int(48, 57)
        if valid_from_day:
            valid_from = datetime.date.min + datetime.timedelta(days=valid_from_day - 1)
        else:
            valid_from = None
        if valid_until_day:
            valid_until = datetime.date.min + datetime.timedelta(days=valid_until_day - 1)
        else:
            valid_until = None

        if d.read_bool(57):
            individual_frequent_traveler_id = d.read_int(58, 105)
            corporate_frequent_traveler_id = None
        else:
            individual_frequent_traveler_id = None
            corporate_frequent_traveler_id = d.read_int(58, 105)

        if d.read_bool(105):
            departure_station_number = d.read_int(106, 126)
            departure_station_name = None
        else:
            departure_station_number = None
            departure_station_name = d.read_string1(106, 136).strip()

        if d.read_bool(136):
            arrival_station_number = d.read_int(137, 157)
            arrival_station_name = None
        else:
            arrival_station_number = None
            arrival_station_name = d.read_string1(137, 167).strip()

        departure_time_slot = d.read_int(167, 173)
        if departure_time_slot:
            departure_time = (
                    datetime.datetime.min +
                    datetime.timedelta(minutes=(departure_time_slot - 1) * 30)
            ).time()
        else:
            departure_time = None

        return cls(
            version=version,
            issuer_rics=d.read_int(4, 18),
            return_included=d.read_bool(18),
            number_tickets=d.read_int(19, 25),
            number_adults=d.read_int(25, 32),
            number_children=d.read_int(32, 39),
            valid_from=valid_from,
            valid_until=valid_until,
            corporate_frequent_traveler_id=corporate_frequent_traveler_id,
            individual_frequent_traveler_id=individual_frequent_traveler_id,
            departure_station_number=departure_station_number,
            departure_station_name=departure_station_name,
            arrival_station_number=arrival_station_number,
            arrival_station_name=arrival_station_name,
            departure_time=departure_time,
            train_number=d.read_int(173, 190),
            reservation_reference=d.read_int(190, 230),
            travel_class=d.read_string1(230, 236),
            coach_number=d.read_int(236, 246),
            seat=f"{d.read_int(246, 253)}-{d.read_string1(253, 259)}",
            overbooked=d.read_bool(259),
            pnr=d.read_string1(260, 302),
            ticket_type=d.read_int(302, 306),
            specimen=not d.read_bool(306),
        )
