import dataclasses
import decimal
import typing
import datetime

import pytz


class CDException(Exception):
    pass

@dataclasses.dataclass
class Reservation:
    train: str
    carriage: str
    seat: str


@dataclasses.dataclass
class CDRecordUT:
    ticket_type: typing.Optional[str]
    name: typing.Optional[str]
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
    def parse(cls, data: bytes, version: int):
        if version != 1:
            raise CDException(f"Unsupported record version {version}")

        tz = pytz.timezone("Europe/Prague")

        name = None
        validity_start = None
        validity_end = None
        pnr = None
        reference = None
        distance = None
        ticket_type = None
        reservations = []
        return_reservations = []
        route_uic = None
        origin_uic = None
        destination_uic = None
        seller_id = None
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
            elif block_id == "KS":
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
                try:
                    origin_uic = 5400000 + int(block_data[:-1], 10)
                except ValueError as e:
                    raise CDException(f"Invalid origin station ID") from e
            elif block_id == "SD":
                try:
                    destination_uic = 5400000 + int(block_data[:-1], 10)
                except ValueError as e:
                    raise CDException(f"Invalid destination station ID") from e
            elif block_id == "RT":
                reservations = cls.parse_reservations(block_data)
            elif block_id == "RZ":
                return_reservations = cls.parse_reservations(block_data)
            elif block_id == "VY":
                seller_id = block_data
            elif block_data:
                blocks[block_id] = block_data

        return cls(
            name=name,
            validity_start=validity_start,
            validity_end=validity_end,
            pnr=pnr,
            reference=reference,
            distance=distance,
            ticket_type=ticket_type,
            reservations=reservations,
            return_reservations=return_reservations,
            route_uic=route_uic,
            origin_uic=origin_uic,
            destination_uic=destination_uic,
            seller_id=seller_id,
            other_blocks=blocks,
        )