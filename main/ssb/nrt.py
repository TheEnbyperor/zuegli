import dataclasses
import datetime
import typing
from django.utils import timezone
from . import util

@dataclasses.dataclass
class NonReservationTicket:
    specimen: bool
    num_adults: int
    num_children: int
    travel_class: int
    pnr: str
    issuing_date: datetime.date
    return_included: bool
    validity_start: datetime.date
    validity_end: datetime.date
    departure_station_uic: typing.Optional[int]
    arrival_station_uic: typing.Optional[int]
    departure_station_name: typing.Optional[str]
    arrival_station_name: typing.Optional[str]
    passenger_name: str
    countermark: int
    information_message: int
    extra_text: str

    @staticmethod
    def type():
        return "NRT"

    @classmethod
    def parse(cls, data: util.BitStream):
        year = data.read_int(105, 109)
        issuing_day = data.read_int(109, 118)
        validity_start_day = data.read_int(119, 128)
        validity_end_day = data.read_int(128, 137)

        now = timezone.now()
        year = ((now.year // 10) * 10) + year
        year_start = datetime.date(year, 1, 1)
        if year_start > now.date():
            year_start = year_start.replace(year=year_start.year - 10)
        issuing_date = year_start + datetime.timedelta(days=issuing_day - 1)
        validity_start = issuing_date + datetime.timedelta(days=validity_start_day)
        validity_end = issuing_date + datetime.timedelta(days=validity_end_day)

        departure_station_uic = None
        arrival_station_uic = None
        departure_station_name = None
        arrival_station_name = None

        station_code_flag = data.read_bool(137)
        if not station_code_flag:
            station_code_table = data.read_int(138, 142)
            if station_code_table == 1:
                departure_station_uic = data.read_int(142, 170)
                arrival_station_uic = data.read_int(170, 198)
        else:
            departure_station_name = data.read_string(138, 168)
            arrival_station_name = data.read_string(168, 198)

        return cls(
            specimen=data.read_bool(14),
            num_adults=data.read_int(0, 7),
            num_children=data.read_int(7, 14),
            travel_class=data.read_int(15, 21),
            pnr=data.read_string(21, 105),
            issuing_date=issuing_date,
            return_included=data.read_bool(118),
            validity_start=validity_start,
            validity_end=validity_end,
            departure_station_uic=departure_station_uic,
            arrival_station_uic=arrival_station_uic,
            departure_station_name=departure_station_name,
            arrival_station_name=arrival_station_name,
            passenger_name=data.read_string(198, 270),
            countermark=data.read_int(270, 278),
            information_message=data.read_int(278, 292),
            extra_text=data.read_string(292, 436),
        )