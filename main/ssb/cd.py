import dataclasses
import decimal
import typing
import datetime
from django.utils import timezone
from . import util
from ..uic import cd

@dataclasses.dataclass
class CDData:
    price: typing.Optional[decimal.Decimal]
    distance: typing.Optional[decimal.Decimal]
    other_blocks: typing.Dict[str, str]

    @classmethod
    def parse(cls, data: str):
        blocks = data.split(",")

        price = None
        distance = None
        other_blocks = {}

        for block in blocks:
            block_id = block[0]
            block_data = block[1:]

            if block_id == "C":
                try:
                    price = decimal.Decimal(block_data) / decimal.Decimal("100")
                except ValueError as e:
                    raise cd.CDException("Invalid price") from e
            elif block_id == "D":
                try:
                    distance = decimal.Decimal(block_data)
                except ValueError as e:
                    raise cd.CDException("Invalid distance") from e
            else:
                other_blocks[block_id] = block_data

        return cls(
            price=price,
            distance=distance,
            other_blocks=other_blocks
        )

    def price_str(self):
        return f"Kč {self.price:.2f}"


@dataclasses.dataclass
class Ticket:
    number_adults: int
    number_children: int
    specimen: bool
    travel_class: int
    pnr: str
    issuing_date: datetime.date
    return_included: bool
    validity_start: datetime.date
    validity_end: datetime.date
    station_code_table: typing.Optional[int]
    departure_station: util.Station
    arrival_station: util.Station
    flags: cd.OneTicketFlags
    extra_text: str
    sjt_timestamp: int

    @staticmethod
    def type():
        return "CD"

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

        station_code_table = None
        station_code_flag = data.read_bool(120)
        if not station_code_flag:
            station_code_table = data.read_int(121, 125)
            if station_code_table == 1:
                departure_station = util.Station(id=data.read_int(125, 153), type="uic")
                arrival_station = util.Station(id=data.read_int(153, 181), type="uic")
            else:
                departure_station = util.Station(id=data.read_int(125, 153), type="other")
                arrival_station = util.Station(id=data.read_int(153, 181), type="other")
        else:
            departure_station = util.Station(id=data.read_string(125, 153), type="name")
            arrival_station = util.Station(id=data.read_string(153, 181), type="name")

        return cls(
            number_adults=data.read_int(0, 7),
            number_children=data.read_int(7, 14),
            specimen=data.read_bool(14),
            travel_class=data.read_int(15, 21),
            pnr=data.read_string(21, 105),
            issuing_date=issuing_date,
            return_included=data.read_bool(118),
            validity_start=validity_start,
            validity_end=validity_end,
            station_code_table=station_code_table,
            departure_station=departure_station,
            arrival_station=arrival_station,
            flags=cd.OneTicketFlags.from_int(data.read_int(198, 212)),
            extra_text=data.read_string(212, 422),
            sjt_timestamp=data.read_int(422, 434)
        )