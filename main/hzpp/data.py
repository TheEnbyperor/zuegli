import dataclasses
import datetime
import decimal
import typing
import pytz
from . import util


@dataclasses.dataclass
class JourneySegment:
    origin_station: int
    destination_station: int
    travel_class: str

    @classmethod
    def parse(cls, data: typing.List[str]) -> typing.Optional["JourneySegment"]:
        if len(data) != 5:
            raise util.HZPPException("Invalid journey segment length")

        try:
            origin_station = int(data[0], 10) + 7800000
        except ValueError:
            raise util.HZPPException("Invalid origin station ID")

        try:
            destination_station = int(data[1], 10) + 7800000
        except ValueError:
            raise util.HZPPException("Invalid destination station ID")

        return cls(
            origin_station=origin_station,
            destination_station=destination_station,
            travel_class=data[3],
            # values 2 and 4 unknown
        ) if data[0] or data[1] else None


@dataclasses.dataclass
class HZPPTicket:
    ticket_number: str
    product_code: str
    price: decimal.Decimal
    outbound_journey: JourneySegment
    return_journey: typing.Optional[JourneySegment]
    valid_from: datetime.datetime
    valid_until: datetime.datetime

    @classmethod
    def parse(cls, data: bytes) -> "HZPPTicket":
        try:
            data = data.decode("iso-8859-1")
        except UnicodeDecodeError as e:
            raise util.HZPPException("Invalid ticket encoding") from e

        if data[:2] != "B1":
            raise util.HZPPException("Not a HŽPP ticket")

        parts = data[2:].split("|")

        if len(parts) < 14:
            raise util.HZPPException("Ticket too short")

        try:
            price_int = int(parts[2], 10)
            price = decimal.Decimal(price_int) / decimal.Decimal("100")
        except ValueError as e:
            raise util.HZPPException("Invalid ticket price") from e

        tz = pytz.timezone("Europe/Zagreb")

        try:
            valid_from_int = int(parts[13], 10)
            valid_from = tz.localize(
                datetime.datetime(2003, 1, 1, 0, 0, 0) +
                datetime.timedelta(minutes=valid_from_int)
            )
        except ValueError as e:
            raise util.HZPPException("Invalid ticket valid from") from e

        try:
            valid_to_int = int(parts[14], 10)
            valid_to = tz.localize(
                datetime.datetime(2003, 1, 1, 0, 0, 0) +
                datetime.timedelta(minutes=valid_to_int)
            )
        except ValueError as e:
            raise util.HZPPException("Invalid ticket valid to") from e

        return cls(
            ticket_number=parts[0],
            product_code=parts[1],
            price=price,
            outbound_journey=JourneySegment.parse(parts[3:8]),
            return_journey=JourneySegment.parse(parts[8:13]),
            valid_from=valid_from,
            valid_until=valid_to,
        )

    def price_str(self):
        if self.valid_from >= pytz.timezone("Europe/Zagreb").localize(datetime.datetime(2023, 1, 1, 0, 0, 0)):
            return f"{self.price:.2f} €"
        else:
            return f"{self.price:.2f} HRK"