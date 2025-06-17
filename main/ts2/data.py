import dataclasses
import datetime
import typing
from .util import TS2Exception

@dataclasses.dataclass
class TicketData:
    ticket_id: str
    valid_from: datetime.date
    valid_to: datetime.date
    customer_name: str
    customer_dob: datetime.date
    layout_lines: typing.List[str]

    @classmethod
    def parse(cls, data: bytes) -> "TicketData":
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise TS2Exception("TS2 ticket data cannot be decoded") from e

        try:
            valid_from = datetime.datetime.strptime(data[37:45], "%d%m%Y").date()
            valid_to = datetime.datetime.strptime(data[45:53], "%d%m%Y").date()
        except ValueError as e:
            raise TS2Exception("Invalid validity date") from e

        try:
            customer_dob = datetime.datetime.strptime(data[90:98], "%d%m%Y").date()
        except ValueError as e:
            raise TS2Exception("Invalid customer date of birth") from e

        layout_lines = [data[i:i+25] for i in range(98, len(data), 25)]

        return cls(
            # 0 Unknown
            ticket_id=data[1:33],
            # 33 - 37 Unknown
            valid_from=valid_from,
            valid_to=valid_to,
            customer_name=data[53:90].strip(),
            customer_dob=customer_dob,
            layout_lines=layout_lines,
        )