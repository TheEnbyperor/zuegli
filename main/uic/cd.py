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
    other_blocks: typing.Dict[str, str]

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
            elif block_id == "KD":
                ticket_type = block_data
            elif block_id == "KC":
                reference = block_data
            elif block_id == "KK":
                pnr = block_data
            elif block_id == "KM":
                try:
                    distance = decimal.Decimal(block_data)
                except ValueError as e:
                    raise CDException(f"Invalid distance") from e
            elif block_id == "OD":
                try:
                    validity_start = tz.localize(
                        datetime.datetime.strptime(block_data, "%d.%m.%Y %H:%M")
                    ).astimezone(pytz.utc)
                except ValueError as e:
                    raise CDException(f"Invalid validity start date") from e
            elif block_id == "DO":
                try:
                    validity_end = tz.localize(
                        datetime.datetime.strptime(block_data, "%d.%m.%Y %H:%M")
                    ).astimezone(pytz.utc)
                except ValueError as e:
                    raise CDException(f"Invalid validity end date") from e
            elif block_id == "RT":
                reservations = []
                for res in block_data.split("#"):
                    parts = res.split("|")
                    if len(parts) != 3:
                        raise CDException(f"Invalid reservation")
                    reservations.append(Reservation(
                        train=parts[0],
                        carriage=parts[1],
                        seat=parts[2],
                    ))
            else:
                blocks[block_id] = block_data

        return cls(
            name=name,
            validity_start=validity_start,
            validity_end=validity_end,
            other_blocks=blocks,
            pnr=pnr,
            reference=reference,
            distance=distance,
            ticket_type=ticket_type,
            reservations=reservations,
        )