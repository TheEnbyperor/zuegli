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
class Extra:
    type_of_addon: int
    extension_type: int
    extension_train_type: int
    product_id: int
    price: decimal.Decimal
    unique_extra_id: int
    start_station: int
    end_station: int
    validity_date: datetime.datetime
    train_number: typing.Optional[int]

    def price_str(self):
        return f"{self.price:.2f} €"


@dataclasses.dataclass
class Ticket:
    format_type: int
    tariff_location_id: int
    product_id: int
    status_id: int
    unique_ticket_id: int
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
    extras: typing.List[Extra]

    @staticmethod
    def type():
        return "SZ_TK"

    @property
    def pnr(self):
        return str(self.unique_ticket_id)

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
    def parse(cls, data: util.BitStream, version: int):
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

        extras = []
        if version >= 3:
            for extra in range(0, data.read_int(464, 472)):
                offset = 196 * extra
                extras.append(Extra(
                    type_of_addon=data.read_int(472 + offset, 480 + offset),
                    extension_type=data.read_int(480 + offset, 488 + offset),
                    extension_train_type=data.read_int(488 + offset, 496 + offset),
                    product_id=data.read_int(496 + offset, 512 + offset),
                    price=decimal.Decimal(data.read_int(512 + offset, 528 + offset)) / decimal.Decimal(100),
                    unique_extra_id=data.read_int(528 + offset, 576 + offset),
                    start_station=data.read_int(576 + offset, 608 + offset),
                    end_station=data.read_int(608 + offset, 640 + offset),
                    validity_date=cls.parse_dt(data.read_int(640 + offset, 672 + offset)),
                    train_number=data.read_int(672 + offset, 688 + offset),
                ))

        return cls(
            format_type=data.read_int(0, 8),
            tariff_location_id=data.read_int(8, 24),
            product_id=data.read_int(24, 40),
            status_id=data.read_int(40, 56),
            unique_ticket_id=data.read_int(56, 104),
            bill_number=data.read_int(104, 136),
            price=decimal.Decimal(data.read_int(136, 152)) / decimal.Decimal(100),
            total_price=decimal.Decimal(data.read_int(152, 168)) / decimal.Decimal(100),
            num_travellers=data.read_int(168, 176),
            discount_id=data.read_int(176, 192),
            valid_from=cls.parse_dt(data.read_int(192, 224)),
            valid_to=cls.parse_dt(data.read_int(224, 256)),
            service_provider=data.read_int(256, 272),
            stations=stations,
            distance=decimal.Decimal(data.read_int(432, 448)) / decimal.Decimal(10),
            one_way=bool(data.read_int(448, 456)),
            reprint_number=data.read_int(456, 464),
            extras=extras,
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
