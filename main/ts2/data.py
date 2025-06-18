import dataclasses
import datetime
import typing
from .util import TS2Exception

@dataclasses.dataclass
class TicketData:
    ticket_type: str
    ticket_id: str
    vvt_ticket_id: str
    card_issue: str
    valid_from: datetime.date
    valid_to: datetime.date
    customer_forename: str
    customer_surname: str
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

        customer_name = data[53:90].strip().split(",", 1)
        customer_surname = customer_name[0].strip()
        customer_forename = customer_name[1].strip() if len(customer_name) > 1 else ""

        return cls(
            ticket_type=data[0],
            ticket_id=data[1:17],
            vvt_ticket_id=data[17:33],
            card_issue=data[34:37],
            valid_from=valid_from,
            valid_to=valid_to,
            customer_forename=customer_forename,
            customer_surname=customer_surname,
            customer_dob=customer_dob,
            layout_lines=layout_lines,
        )