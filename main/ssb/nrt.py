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
    station_code_table: typing.Optional[int]
    departure_station: util.Station
    arrival_station: util.Station
    information_message: int
    extra_text: str

    @staticmethod
    def type():
        return "NRT"

    @classmethod
    def parse(cls, data: util.BitStream, issuer_rics: int):
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

        station_code_table = None
        station_code_flag = data.read_bool(137)
        if issuer_rics == 3018:
            departure_station = util.Station(id=data.read_string(138, 168), type="benerail")
            arrival_station = util.Station(id=data.read_string(168, 198), type="benerail")
        else:
            if not station_code_flag:
                station_code_table = data.read_int(138, 142)
                if station_code_table == 1:
                    departure_station = util.Station(id=data.read_int(142, 170), type="uic")
                    arrival_station = util.Station(id=data.read_int(170, 198), type="uic")
                else:
                    departure_station = util.Station(id=data.read_int(142, 170), type="other")
                    arrival_station = util.Station(id=data.read_int(170, 198), type="other")
            else:
                if issuer_rics in (1080, 1088):
                    departure_station = util.Station(id=data.read_int(138, 168) % 10000000, type="uic")
                    arrival_station = util.Station(id=data.read_int(168, 198) % 10000000, type="uic")
                    if 8000000 <= departure_station.id <= 8099999:
                        departure_station.type = "db_hafas"
                    if 8000000 <= arrival_station.id <= 8099999:
                        arrival_station.type = "db_hafas"
                else:
                    departure_station = util.Station(id=data.read_string(138, 168), type="name")
                    arrival_station = util.Station(id=data.read_string(168, 198), type="name")

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
            station_code_table=station_code_table,
            departure_station=departure_station,
            arrival_station=arrival_station,
            information_message=data.read_int(198, 212),
            extra_text=data.read_string(212, 434),
        )