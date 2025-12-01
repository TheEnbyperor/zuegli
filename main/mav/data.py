import dataclasses
import datetime
import struct
import typing
import pytz
from .util import MavException
from . import envelope

TZ = pytz.timezone("Europe/Budapest")
EPOCH = datetime.datetime(2016, 12, 31, 23, 0, 0, tzinfo=pytz.utc)

@dataclasses.dataclass
class PassengerData:
    name: str
    dob: typing.Optional[datetime.date]
    id_card_number: str

@dataclasses.dataclass
class TripData:
    ticket_type: bytes
    origin: int
    destination: int
    outbound_via: typing.List[int]
    return_via: typing.List[int]
    travel_class: str
    specimen: bool
    valid_from: datetime.datetime
    valid_until: datetime.datetime
    num_passengers: int
    passenger_type: bytes

@dataclasses.dataclass
class SeatReservation:
    ticket_type: bytes
    origin: int
    destination: int
    departure: datetime.datetime
    operator: int
    train_number: str
    num_passengers: int
    coach: str
    seat: int

@dataclasses.dataclass
class PassData:
    pass_type: bytes
    valid_from: datetime.datetime
    valid_until: datetime.datetime
    num_passengers: int


@dataclasses.dataclass
class TicketData:
    issued_at: datetime.datetime
    price: float
    ticket_medium: bytes
    passenger_data: typing.Optional[PassengerData]
    trip_data: typing.Optional[TripData]
    seat_reservations: typing.List[SeatReservation]
    passes: typing.List[PassData]

    @property
    def ticket_medium_name(self):
        if self.ticket_medium == b"\x23\x6d\x05\x20":
            return "PDF from App"
        elif self.ticket_medium == b"\x33\x87\x97\xfe":
            return "PDF from Web"
        elif self.ticket_medium == b"\x54\xa5\xb3\x4d":
            return "Thermal Paper from EMKE"
        elif self.ticket_medium == b"\xf8\xb4\x05\xcd":
            return "Thermal Paper from Ticket Inspector"
        elif self.ticket_medium == b"\x69\x1b\x8d\x67":
            return "Hologram Paper from Volanbusz"
        elif self.ticket_medium == b"\xa7\xd5\x9e\xa6":
            return "Paper from Vending Machine"
        elif self.ticket_medium == b"\xc7\x85\xb6\x0c":
            return "Paper BKK"
        else:
            return f"Unknown: {self.ticket_medium.hex()}"

    @classmethod
    def parse(cls, data: envelope.Envelope) -> "TicketData":
        issued_at = EPOCH + datetime.timedelta(seconds=int.from_bytes(data.data[:4], "big"))
        price = struct.unpack("!f", data.data[4:8])[0]

        has_passenger_block = bool(data.data[8] & 0x80)
        has_trip_block = bool(data.data[8] & 0x01)
        num_class_upgrades = data.data[9]
        num_seat_reservations = data.data[10]
        num_passes = data.data[11]

        ticket_medium = data.data[15:19]

        offset = 19
        if has_passenger_block:
            dob_int = int.from_bytes(data.data[offset+45:offset+49], "big")
            try:
                passenger_data = PassengerData(
                    name=data.data[offset:offset+45].rstrip(b"\x00").decode("utf-8"),
                    dob=datetime.date(
                        year=dob_int // 10000,
                        month=(dob_int // 100) % 100,
                        day=dob_int % 100
                    ) if dob_int else None,
                    id_card_number=data.data[offset+49:offset+64].rstrip(b"\x00").decode("utf-8")
                )
            except UnicodeDecodeError as e:
                raise MavException("Invalid passenger data") from e
            offset += 64
        else:
            passenger_data = None

        if has_trip_block:
            valid_from = EPOCH + datetime.timedelta(seconds=int.from_bytes(data.data[offset+102:offset+106], "big"))
            trip_data = TripData(
                ticket_type=data.data[offset:offset+4],
                origin=int.from_bytes(data.data[offset+4:offset+7], "big"),
                destination=int.from_bytes(data.data[offset+7:offset+10], "big"),
                outbound_via=[int.from_bytes(data.data[i:i+3]) for i in range(offset+10, offset+55, 3) if data.data[i:i+3] != b"\x00\x00\x00"],
                return_via=[int.from_bytes(data.data[i:i+3]) for i in range(offset+55, offset+100, 3) if data.data[i:i+3] != b"\x00\x00\x00"],
                travel_class=data.data[offset+100:offset+101].decode("utf-8"),
                specimen=bool(data.data[offset+101]),
                valid_from=valid_from.astimezone(TZ),
                valid_until=(valid_from + datetime.timedelta(minutes=int.from_bytes(data.data[offset+106:offset+109], "big"))).astimezone(TZ),
                num_passengers=data.data[offset+109],
                passenger_type=data.data[offset+110:offset+114],
            )
            offset += 114
        else:
            trip_data = None

        seat_reservations = []
        for _ in range(num_seat_reservations):
            seat_reservations.append(SeatReservation(
                origin=int.from_bytes(data.data[offset:offset+3], "big"),
                destination=int.from_bytes(data.data[offset+3:offset+6], "big"),
                ticket_type=data.data[offset+6:offset+10],
                departure=(EPOCH + datetime.timedelta(seconds=int.from_bytes(data.data[offset+10:offset+14], "big"))).astimezone(TZ),
                operator=int.from_bytes(data.data[offset+14:offset+16], "big"),
                train_number=data.data[offset+16:offset+36].rstrip(b"\x00").decode("utf-8"),
                num_passengers=data.data[offset+36],
                coach=data.data[offset+37:offset+40].rstrip(b"\x00").decode("utf-8"),
                seat=int.from_bytes(data.data[offset+40:offset+42], "big"),
            ))
            offset += 72

        passes = []
        for _ in range(num_passes):
            valid_from = EPOCH + datetime.timedelta(seconds=int.from_bytes(data.data[offset+12:offset+16], "big"))
            passes.append(PassData(
                pass_type=data.data[offset:offset+12],
                valid_from=valid_from.astimezone(TZ),
                valid_until=(valid_from + datetime.timedelta(minutes=int.from_bytes(data.data[offset+16:offset+19], "big"))).astimezone(TZ),
                num_passengers=data.data[offset+19],
            ))
            offset += 20

        return cls(
            issued_at=issued_at,
            price=price,
            ticket_medium=ticket_medium,
            passenger_data=passenger_data,
            trip_data=trip_data,
            seat_reservations=seat_reservations,
            passes=passes,
        )

    @property
    def price_str(self):
        return f"{self.price:.2f} Ft"