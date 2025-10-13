import dataclasses
import decimal
import enum
import typing
import datetime
import base64
import hashlib
import pytz
from .. import ticket


class CDException(Exception):
    pass

@dataclasses.dataclass
class Reservation:
    train: str
    carriage: str
    seat: str

@dataclasses.dataclass
class Tariff:
    tariff_code: str
    number_passengers: int

class OneTicketType(enum.Enum):
    OpenTicket = 22
    Reservation = 23
    SingleTicket = 24
    GroupTicket = 25
    Subscription = 27
    DisabilityCard = 29

    def name(self):
        if self == self.OpenTicket:
            return "Open ticket"
        elif self == self.Reservation:
            return "Reservation"
        elif self == self.SingleTicket:
            return "Single ticket"
        elif self == self.GroupTicket:
            return "Group ticket"
        elif self == self.Subscription:
            return "Subscription"
        elif self == self.DisabilityCard:
            return "Disability card"


class OneTicketTravelType(enum.Enum):
    Network = 0
    Route = 1
    Zone = 2
    ZonePlusSingle = 3
    ZonePlusNetwork = 4
    ZonePlusRoute = 5

    def name(self):
        if self == self.Network:
            return "Network ticket"
        elif self == self.Route:
            return "Route ticket"
        elif self == self.Zone:
            return "Zonal ticket"
        elif self == self.ZonePlusSingle:
            return "Zonal ticket plus single ticket"
        elif self == self.ZonePlusNetwork:
            return "Zonal ticket plus network ticket"
        elif self == self.ZonePlusRoute:
            return "Zonal ticket plus route ticket"


@dataclasses.dataclass
class OneTicketFlags:
    check_passenger_id: bool
    check_passenger_rail_pass: bool
    check_fare_discounts: bool
    secure_paper: bool
    check_in_card: bool
    zone_travel_document: bool
    contains_zone_component: bool
    additional_payment_ticket: bool
    reservation_only_ticket: bool

    @classmethod
    def from_int(cls, value: int) -> "OneTicketFlags":
        return cls(
            check_passenger_id=bool(value & 0b0000000000000001),
            check_passenger_rail_pass=bool(value & 0b0000000000000010),
            check_fare_discounts=bool(value & 0b0000000010000000),
            secure_paper=bool(value & 0b0000000100000000),
            check_in_card=bool(value & 0b0000001000000000),
            zone_travel_document=bool(value & 0b0000010000000000),
            contains_zone_component=bool(value & 0b0000100000000000),
            additional_payment_ticket=bool(value & 0b0001000000000000),
            reservation_only_ticket=bool(value & 0b0010000000000000),
        )


@dataclasses.dataclass
class CDRecordUT:
    ticket_type: typing.Optional[str]
    one_ticket_type: typing.Optional[OneTicketType]
    name: typing.Optional[str]
    date_of_birth: typing.Optional[datetime.date]
    validity_start: typing.Optional[datetime.datetime]
    validity_end: typing.Optional[datetime.datetime]
    pnr: typing.Optional[str]
    reference: typing.Optional[str]
    distance: typing.Optional[decimal.Decimal]
    reservations: typing.List[Reservation]
    return_reservations: typing.List[Reservation]
    origin_uic: typing.Optional[int]
    destination_uic: typing.Optional[int]
    route_uic: typing.Optional[typing.List[int]]
    seller_id: typing.Optional[str]
    email_hash: typing.Optional[bytes]
    email: typing.Optional[str]
    travel_type: typing.Optional[OneTicketTravelType]
    linked_validation_required: typing.Optional[bool]
    tariffs: typing.List[Tariff]
    one_ticket_flags: typing.Optional[OneTicketFlags]
    other_blocks: typing.Dict[str, str]

    @staticmethod
    def parse_reservations(data: str) -> typing.List[Reservation]:
        reservations = []
        for res in data.split("#"):
            parts = res.split("|")
            if len(parts) != 3:
                raise CDException(f"Invalid reservation")
            reservations.append(Reservation(
                train=parts[0],
                carriage=parts[1],
                seat=parts[2],
            ))
        return reservations

    @classmethod
    def parse(cls, data: bytes, version: int, context: "ticket.TicketContexts"):
        if version != 1:
            raise CDException(f"Unsupported record version {version}")

        tz = pytz.timezone("Europe/Prague")

        name = None
        date_of_birth = None
        validity_start = None
        validity_end = None
        pnr = None
        reference = None
        distance = None
        ticket_type = None
        one_ticket_type = None
        reservations = []
        return_reservations = []
        route_uic = None
        origin_uic = None
        destination_uic = None
        seller_id = None
        email_hash = None
        email = None
        travel_type = None
        linked_validation_required = None
        one_ticket_flags = None
        tariffs = []
        blocks = {}

        offset = 0
        while data[offset:]:
            try:
                block_id = data[offset:offset + 2].decode("utf-8")
            except UnicodeDecodeError as e:
                raise CDException(f"Invalid CD UT record") from e
            try:
                block_len = int(data[offset + 2:offset + 5].decode("utf-8"), 10)
            except (ValueError, UnicodeDecodeError) as e:
                raise CDException(f"Invalid CD UT record") from e
            try:
                block_data = data[offset + 5:offset + 5 + block_len].decode("utf-8")
            except UnicodeDecodeError as e:
                raise CDException(f"Invalid CD UT record") from e
            offset += 5 + block_len

            if block_id == "KJ":
                name = block_data
            elif block_id == "JP":
                name = block_data
            elif block_id == "KD":
                ticket_type = block_data
            elif block_id == "KC":
                reference = block_data
            elif block_id == "KK":
                pnr = block_data
            elif block_id in ("KM", "VZ"):
                try:
                    distance = decimal.Decimal(block_data)
                except ValueError as e:
                    raise CDException(f"Invalid distance") from e
            elif block_id in ("KS", "SP"):
                if block_data != "0":
                    try:
                        route_uic = [int(v) for v in block_data.split("|")]
                    except ValueError as e:
                        raise CDException(f"Invalid station ID") from e
            elif block_id == "OD":
                try:
                    validity_start = tz.localize(
                        datetime.datetime.strptime(block_data, "%d.%m.%Y %H:%M")
                    )
                except ValueError as e:
                    raise CDException(f"Invalid validity start date") from e
            elif block_id == "DO":
                try:
                    validity_end = tz.localize(
                        datetime.datetime.strptime(block_data, "%d.%m.%Y %H:%M")
                    )
                except ValueError as e:
                    raise CDException(f"Invalid validity end date") from e
            elif block_id == "PO":
                try:
                    validity_start = tz.localize(
                        datetime.datetime.strptime(block_data, "%d%m%Y%H%M")
                    )
                except ValueError as e:
                    raise CDException(f"Invalid validity start date") from e
            elif block_id == "PD":
                try:
                    validity_end = tz.localize(
                        datetime.datetime.strptime(block_data, "%d%m%Y%H%M")
                    )
                except ValueError as e:
                    raise CDException(f"Invalid validity end date") from e
            elif block_id == "SZ":
                if block_data[:-1]:
                    try:
                        origin_uic = 5400000 + int(block_data[:-1], 10)
                    except ValueError as e:
                        raise CDException(f"Invalid origin station ID") from e
            elif block_id == "SD":
                if block_data[:-1]:
                    try:
                        destination_uic = 5400000 + int(block_data[:-1], 10)
                    except ValueError as e:
                        raise CDException(f"Invalid destination station ID") from e
            elif block_id in ("RT", "RE"):
                reservations = cls.parse_reservations(block_data)
            elif block_id == "RZ":
                return_reservations = cls.parse_reservations(block_data)
            elif block_id == "VY":
                seller_id = block_data
            elif block_id == "EM":
                try:
                    email_hash = base64.b64decode(block_data)
                except ValueError as e:
                    raise CDException(f"Invalid email hash") from e

                for c in context.contexts:
                    if c.email and hashlib.sha512(c.email.encode("utf-8")).digest()[:8] == email_hash:
                        email = c.email
                        break
            elif block_id == "DJ":
                one_ticket_type = OneTicketType(int(block_data, 10))
            elif block_id == "CT":
                travel_type = OneTicketTravelType(int(block_data, 10))
            elif block_id == "DN":
                date_of_birth = datetime.datetime.strptime(block_data, "%d%m%Y").date()
            elif block_id == "OT":
                if block_data == "1":
                    linked_validation_required = True
                elif block_data == "0":
                    linked_validation_required = False
                else:
                    raise CDException(f"Invalid linked validation required flag")
            elif block_id == "TF":
                for t in block_data.split("|"):
                    if len(t) != 4:
                        raise CDException(f"Invalid tariff")
                    tariffs.append(Tariff(
                        tariff_code=t[0:2],
                        number_passengers=int(t[2:4], 10),
                    ))
            elif block_id == "IZ":
                one_ticket_flags = OneTicketFlags.from_int(int(block_data, 10))
            elif block_data:
                blocks[block_id] = block_data

        return cls(
            name=name,
            date_of_birth=date_of_birth,
            validity_start=validity_start,
            validity_end=validity_end,
            pnr=pnr,
            reference=reference,
            distance=distance,
            ticket_type=ticket_type,
            one_ticket_type=one_ticket_type,
            reservations=reservations,
            return_reservations=return_reservations,
            route_uic=route_uic,
            origin_uic=origin_uic,
            destination_uic=destination_uic,
            seller_id=seller_id,
            email_hash=email_hash,
            email=email,
            travel_type=travel_type,
            linked_validation_required=linked_validation_required,
            tariffs=tariffs,
            one_ticket_flags=one_ticket_flags,
            other_blocks=blocks,
        )

    @property
    def email_hash_hex(self):
        return ":".join(f"{b:02x}" for b in self.email_hash)