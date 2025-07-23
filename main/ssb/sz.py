import dataclasses
import decimal
import datetime
import typing

import pytz

from . import util

@dataclasses.dataclass
class Station:
    station_type: int
    station_id: int

@dataclasses.dataclass
class Ticket:
    format_type: int
    tariff_location_id: int
    product_id: int
    status_id: int
    reference: int
    bill_number: int
    price: decimal.Decimal
    total_price: decimal.Decimal
    num_travellers: int
    discount_id: int
    valid_from: datetime.datetime
    valid_to: datetime.datetime
    service_provider: int
    stations: typing.List[Station]
    distance: decimal.Decimal
    one_way: bool
    reprint_number: int

    @staticmethod
    def type():
        return "SZ_TK"

    @property
    def pnr(self):
        return str(self.reference)

    @staticmethod
    def parse_dt(data: int):
        tz = pytz.timezone("Europe/Ljubljana")

        sec = data & 0b111111
        data >>= 6
        min = data & 0b111111
        data >>= 6
        hour = data & 0b11111
        data >>= 5
        day = data & 0b11111
        data >>= 5
        month = data & 0b1111
        data >>= 4
        year = (data & 0b111111) + 2002
        return tz.localize(
            datetime.datetime(year, month, day, hour, min, sec)
        )

    @classmethod
    def parse(cls, data: util.BitStream):
        stations = []
        if t := data.read_int(272, 274):
            stations.append(Station(
                station_type=t,
                station_id=data.read_int(274, 304),
            ))
        if t := data.read_int(304, 306):
            stations.append(Station(
                station_type=t,
                station_id=data.read_int(306, 336),
            ))
        if t := data.read_int(336, 338):
            stations.append(Station(
                station_type=t,
                station_id=data.read_int(338, 368),
            ))
        if t := data.read_int(368, 370):
            stations.append(Station(
                station_type=t,
                station_id=data.read_int(370, 400),
            ))
        if t := data.read_int(400, 402):
            stations.append(Station(
                station_type=t,
                station_id=data.read_int(402, 432),
            ))

        return cls(
            format_type=data.read_int(0, 8),
            tariff_location_id=data.read_int(8, 24),
            product_id=data.read_int(24, 40),
            status_id=data.read_int(40, 56),
            reference=data.read_int(56, 104),
            bill_number=data.read_int(104, 136),
            price=decimal.Decimal(data.read_int(136, 152)) / decimal.Decimal(100),
            total_price=decimal.Decimal(data.read_int(152, 168)) / decimal.Decimal(100),
            num_travellers=data.read_int(168, 176),
            discount_id=data.read_int(176, 192),
            valid_from=Ticket.parse_dt(data.read_int(192, 224)),
            valid_to=Ticket.parse_dt(data.read_int(224, 256)),
            service_provider=data.read_int(256, 272),
            stations=stations,
            distance=decimal.Decimal(data.read_int(432, 448)) / decimal.Decimal(100),
            one_way=bool(data.read_int(448, 456)),
            reprint_number=data.read_int(456, 464),
        )

    def price_str(self):
        return f"{self.price:.2f} €"

    def total_price_str(self):
        return f"{self.total_price:.2f} €"

    def status_str(self):
        if self.status_id == 1:
            return "Redna cena"
        elif self.status_id == 2:
            return "Otroci 6-15"
        elif self.status_id == 4:
            return "Otroci do 6"
        elif self.status_id == 23:
            return "Pes - 50%"
        elif self.status_id == 43:
            return "Skupina do 26 let - 50%"
        elif self.status_id == 66:
            return "Družina odrasli LV - 40%"
        elif self.status_id == 68:
            return "Družina otr do 6 LV - 100%"
        elif self.status_id == 87:
            return "IJPP potnik"
        elif self.status_id == 94:
            return "Spremlj. skupine - 50%"
        else:
            return f"Unknown - {self.status_id}"

    def product_str(self):
        if self.product_id in (1, 3):
            return "Enosmerna vozovnica"
        elif self.product_id in (2, 4):
            return "Povratna vozovnica"
        elif self.product_id == 40:
            return "IZLETka"
        elif self.product_id == 44:
            return "Enkratni dodatek IJPP IC EC EN MV"
        elif self.product_id == 112:
            return "Dnevna vozovnica - kolo"
        elif self.product_id in (131, 145):
            return "Turist vikend"
        elif self.product_id == 153:
            return "Mestna vozovnica"
        elif self.product_id == 167:
            return "Družinska enosmerna"
        elif self.product_id == 209:
            return "Enkratni dodatek IJPP ICS"
        elif self.product_id == 235:
            return "Enosmerna vozovnica za psa"
        elif self.product_id == 237:
            return "Povratna vozovnica za psa"
        else:
            return f"Unknown - {self.product_id}"

    def travel_class(self):
        if self.product_id in (1, 2, 145, 167, 235, 237):
            return "second"
        elif self.product_id in (3, 4, 131):
            return "first"
        else:
            return "notApplicable"
