import dataclasses
import decimal
import datetime
import pytz

from . import util

@dataclasses.dataclass
class Ticket:
    reference: int
    ticket_type: int
    price_level: int
    price: decimal.Decimal
    valid_from: datetime.datetime
    valid_to: datetime.datetime
    num_travellers: int

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
        return cls(
            # 0 - 24 UNKNOWN
            ticket_type=data.read_int(24, 40),
            price_level=data.read_int(40, 56),
            reference=data.read_int(56, 104),
            # 104 - 136 UNKNOWN
            price=decimal.Decimal(data.read_int(136, 152)) / decimal.Decimal(100),
            # 152 - 168 duplicate price, inexplicably
            num_travellers=data.read_int(168, 176),
            # 176 - 192 UNKNOWN
            valid_from=Ticket.parse_dt(data.read_int(192, 224)),
            valid_to=Ticket.parse_dt(data.read_int(224, 256)),
        )

    def price_str(self):
        return f"{self.price:.2f} €"

    def price_level_str(self):
        if self.price_level == 1:
            return "Redna cena"
        elif self.price_level == 2:
            return "Otroci 6-15"
        elif self.price_level == 4:
            return "Otroci do 6"
        elif self.price_level == 43:
            return "Skupina do 26 let - 50%"
        elif self.price_level == 87:
            return "IJPP potnik"
        elif self.price_level == 94:
            return "Spremlj. skupine - 50%"

    def ticket_type_str(self):
        if self.ticket_type == 1:
            return "Enosmerna vozovnica 2R"
        elif self.ticket_type == 2:
            return "Povratna vozovnica 2R"
        elif self.ticket_type == 3:
            return "Enosmerna vozovnica 1R"
        elif self.ticket_type == 4:
            return "Povratna vozovnica 1R"
        elif self.ticket_type == 40:
            return "IZLETka"
        elif self.ticket_type == 44:
            return "Enkratni dodatek IJPP IC EC EN MV"
        elif self.ticket_type == 112:
            return "Dnevna vozovnica - kolo"
        elif self.ticket_type == 131:
            return "Turist vikend 1R"
        elif self.ticket_type == 145:
            return "Turist vikend 2R"
        elif self.ticket_type == 153:
            return "Mestna vozovnica"
        else:
            return f"Unknown - {self.ticket_type}"
