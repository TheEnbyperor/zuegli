import dataclasses
import datetime
import struct
import typing
from .util import MavException
from . import envelope

EPOCH = datetime.datetime(2016, 12, 31, 23, 0, 0, tzinfo=datetime.timezone.utc)

@dataclasses.dataclass
class PassengerData:
    name: str
    dob: datetime.date
    id_card_number: str

@dataclasses.dataclass
class TripData:
    ticket_type: bytes
    origin: int
    destination: int
    outbound_via: typing.List[int]
    return_via: typing.List[int]
    travel_class: str
    valid_from: datetime.datetime
    valid_minutes: int
    num_passengers: int
    passenger_type: bytes

@dataclasses.dataclass
class TicketData:
    issued_at: datetime.datetime
    price: float
    ticket_medium: bytes
    passenger_data: typing.Optional[PassengerData]
    trip_data: typing.Optional[TripData]

    @classmethod
    def parse(cls, data: envelope.Envelope) -> "TicketData":
        issued_at = EPOCH + datetime.timedelta(seconds=int.from_bytes(data.data[:4], "big"))
        price = struct.unpack("!f", data.data[4:8])[0]

        has_passenger_block = bool(data.data[8] & 0x80)
        has_trip_block = bool(data.data[8] & 0x01)

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
                    ),
                    id_card_number=data.data[offset+49:offset+64].rstrip(b"\x00").decode("utf-8")
                )
            except UnicodeDecodeError as e:
                raise MavException("Invalid passenger data") from e
            offset += 64
        else:
            passenger_data = None

        if has_trip_block:
            trip_data = TripData(
                ticket_type=data.data[offset:offset+4],
                origin=int.from_bytes(data.data[offset+4:offset+7], "big"),
                destination=int.from_bytes(data.data[offset+7:offset+10], "big"),
                outbound_via=[int.from_bytes(data.data[i:i+3]) for i in range(offset+10, offset+55, 3) if data.data[i:i+3] != b"\x00\x00\x00"],
                return_via=[int.from_bytes(data.data[i:i+3]) for i in range(offset+55, offset+100, 3) if data.data[i:i+3] != b"\x00\x00\x00"],
                travel_class=data.data[offset+100:offset+101].decode("utf-8"),
                valid_from=EPOCH + datetime.timedelta(seconds=int.from_bytes(data.data[offset+102:offset+106], "big")),
                valid_minutes=int.from_bytes(data.data[offset+106:offset+109], "big"),
                num_passengers=data.data[offset+109],
                passenger_type=data.data[offset+110:offset+114],
            )
            offset += 114
        else:
            trip_data = None

        return cls(
            issued_at=issued_at,
            price=price,
            ticket_medium=ticket_medium,
            passenger_data=passenger_data,
            trip_data=trip_data
        )

    @property
    def price_str(self):
        return f"{self.price:.2f} HUF"