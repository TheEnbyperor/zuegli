import base64
import dataclasses
import datetime
import typing
from .util import ADIFException


@dataclasses.dataclass
class Ticket:
    ticket_ref: int
    issuer_id: int
    train_number: int
    departure: datetime.datetime
    origin_station: int
    destination_station: int
    via_station: typing.Optional[int]
    carriage: typing.Optional[int]
    seat: typing.Optional[str]
    operator_data: str
    signature: bytes

    def signature_hex(self):
        return ":".join(f"{b:02x}" for b in self.signature)

    @classmethod
    def parse(cls, ticket: bytes) -> "Ticket":
        if len(ticket) != 516:
            raise ADIFException("Invalid length for an ADIF barcode")

        try:
            ticket = ticket.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ADIFException("Invalid ADIF barcode encoding") from e

        try:
            ticket_ref = int(ticket[0:13], 10)
        except ValueError as e:
            raise ADIFException("Invalid ticket reference") from e

        try:
            issuer_id = int(ticket[13:18], 10)
        except ValueError as e:
            raise ADIFException("Invalid issuer RICS") from e

        try:
            train_number = int(ticket[18:23], 10)
        except ValueError as e:
            raise ADIFException("Invalid train number") from e

        try:
            departure = datetime.datetime.strptime(ticket[23:38], "%d/%m/%Y%H:%M")
        except ValueError as e:
            raise ADIFException("Invalid departure time") from e

        try:
            origin_station = int(ticket[38:45], 10)
        except ValueError as e:
            raise ADIFException("Invalid origin station") from e

        try:
            destination_station = int(ticket[45:52], 10)
        except ValueError as e:
            raise ADIFException("Invalid destination station") from e

        if origin_station < 100000:
            origin_station += 7100000
        if destination_station < 100000:
            destination_station += 7100000

        carriage = ticket[52:55].strip()
        if carriage:
            try:
                carriage = int(carriage, 10)
            except ValueError as e:
                raise ADIFException("Invalid carriage") from e
        else:
            carriage = None

        seat = ticket[55:58].strip()
        if not seat:
            seat = None

        try:
            via_station = int(ticket[60:67], 10)
        except ValueError as e:
            raise ADIFException("Invalid via station") from e

        if via_station == 0:
            via_station = None
        elif via_station < 100000:
            via_station += 7100000

        operator_data = ticket[100:416]

        try:
            signature = base64.b64decode(ticket[416:516].rstrip("~"))
        except ValueError as e:
            raise ADIFException("Invalid signature") from e

        return cls(
            ticket_ref=ticket_ref,
            issuer_id=issuer_id,
            train_number=train_number,
            departure=departure,
            origin_station=origin_station,
            destination_station=destination_station,
            via_station=via_station,
            carriage=carriage,
            seat=seat,
            operator_data=operator_data,
            signature=signature,
        )
