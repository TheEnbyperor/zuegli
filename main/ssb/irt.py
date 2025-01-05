import dataclasses
import datetime
import typing
from django.utils import timezone
from . import util

@dataclasses.dataclass
class IntegratedReservationTicket:
    specimen: bool
    num_adults: int
    num_children: int
    travel_class: int
    pnr: str
    issuing_date: datetime.date
    sub_type: int
    departure_station_uic: typing.Optional[int]
    arrival_station_uic: typing.Optional[int]
    station_code_table: typing.Optional[int]
    departure_station_other: typing.Optional[int]
    arrival_station_other: typing.Optional[int]
    departure_station_name: typing.Optional[str]
    arrival_station_name: typing.Optional[str]
    departure_station_benerail: typing.Optional[str]
    arrival_station_benerail: typing.Optional[str]
    departure: datetime.datetime
    train_number: str
    coach_number: int
    seat_number: str
    overbooked: bool
    information_message: int
    extra_text: str

    @staticmethod
    def type():
        return "IRT"

    @classmethod
    def parse(cls, data: util.BitStream, issuer_rics: int):
        year = data.read_int(105, 109)
        issuing_day = data.read_int(109, 118)

        departure_day = data.read_int(181, 190)
        departure_time = data.read_int(190, 201)

        now = timezone.now()
        year = ((now.year // 10) * 10) + year
        year_start = datetime.date(year, 1, 1)
        if year_start > now.date():
            year_start = year_start.replace(year=year_start.year - 10)
        issuing_date = year_start + datetime.timedelta(days=issuing_day - 1)
        departure_date = issuing_date + datetime.timedelta(days=departure_day)
        departure_time = datetime.datetime.combine(departure_date, datetime.time.min) + datetime.timedelta(minutes=departure_time)

        departure_station_uic = None
        arrival_station_uic = None
        departure_station_name = None
        arrival_station_name = None
        station_code_table = None
        departure_station_other = None
        arrival_station_other = None
        departure_station_benerail = None
        arrival_station_benerail = None

        station_code_flag = data.read_bool(120)
        if issuer_rics == 3018:
            departure_station_benerail = data.read_string(121, 151)
            arrival_station_benerail = data.read_string(151, 181)
        else:
            if not station_code_flag:
                station_code_table = data.read_int(121, 125)
                if station_code_table == 1:
                    departure_station_uic = data.read_int(125, 153)
                    arrival_station_uic = data.read_int(153, 181)
                else:
                    departure_station_other = data.read_int(125, 153)
                    arrival_station_other = data.read_int(153, 181)
            else:
                if issuer_rics == 1088:
                    departure_station_uic = data.read_int(121, 151) % 10000000
                    arrival_station_uic = data.read_int(151, 181) % 10000000
                else:
                    departure_station_name = data.read_string(121, 151)
                    arrival_station_name = data.read_string(151, 181)

        return cls(
            specimen=data.read_bool(14),
            num_adults=data.read_int(0, 7),
            num_children=data.read_int(7, 14),
            travel_class=data.read_int(15, 21),
            pnr=data.read_string(21, 105),
            issuing_date=issuing_date,
            sub_type=data.read_int(118, 120),
            departure_station_uic=departure_station_uic,
            arrival_station_uic=arrival_station_uic,
            departure_station_name=departure_station_name,
            arrival_station_name=arrival_station_name,
            station_code_table=station_code_table,
            departure_station_other=departure_station_other,
            arrival_station_other=arrival_station_other,
            departure_station_benerail=departure_station_benerail,
            arrival_station_benerail=arrival_station_benerail,
            departure=departure_time,
            train_number=data.read_string(201, 231),
            coach_number=data.read_int(231, 241),
            seat_number=data.read_string(241, 259),
            overbooked=data.read_bool(259),
            information_message=data.read_int(260, 274),
            extra_text=data.read_string(274, 436),
        )