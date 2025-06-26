import dataclasses
import typing
import datetime
import re
import pytz
from . import layout

TZ = pytz.timezone("Europe/Berlin")
VALID_FROM_RE = re.compile(r"^Von (?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4}) (?P<H>\d{2}):(?P<M>\d{2})$")
VALID_TO_RE = re.compile(r"^Bis (?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4}) (?P<H>\d{2}):(?P<M>\d{2})$")
CUSTOMER_RE = re.compile(r"^(?P<name>[^,]+)(?:, (?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4}))?$")
BOOKED_AT_RE = re.compile(r"^Gebucht:? (?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4}) (?P<H>\d{2}):(?P<M>\d{2}):(?P<S>\d{2})$")


@dataclasses.dataclass
class ParsedPLAI:
    ticket_type: str
    valid_from: typing.Optional[datetime.datetime]
    valid_to: typing.Optional[datetime.datetime]
    conditions: str
    customer_name: str
    customer_dob: typing.Optional[datetime.date]
    booked_at: typing.Optional[datetime.datetime]
    tariff: str


class PLAIParser:
    def __init__(self):
        self.contents = None

    def read(self, content: layout.LayoutV1):
        max_line_len = max(f.column + f.width for f in content.fields)
        max_height = max(f.line + f.height for f in content.fields)
        self.contents = [
            [" " for _ in range(max_line_len)]
            for _ in range(max_height)
        ]

        for field in content.fields:
            x = 0
            y = 0
            for c in field.text:
                if c == "\n":
                    y += 1
                    x = 0
                    continue

                if y + field.line < max_height and x + field.column < max_line_len:
                    self.contents[y + field.line][x + field.column] = c
                x += 1

    def lines(self):
        lines = []
        for l in self.contents:
            lines.append("".join(l).strip())
        return lines

    def parse(self) -> ParsedPLAI:
        lines = self.lines()

        if m := VALID_FROM_RE.match(lines[2]):
            valid_from = datetime.datetime(int(m.group("y")), int(m.group("m")), int(m.group("d")), int(m.group("H")), int(m.group("M")))
            valid_from = TZ.localize(valid_from)
        else:
            valid_from = None

        if m := VALID_TO_RE.match(lines[3]):
            valid_to = datetime.datetime(int(m.group("y")), int(m.group("m")), int(m.group("d")), int(m.group("H")), int(m.group("M")))
            valid_to = TZ.localize(valid_to)
        else:
            valid_to = None

        if m := CUSTOMER_RE.match(lines[8]):
            customer_name = m.group("name")
            if m.group("d"):
                customer_dob = datetime.date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
            else:
                customer_dob = None
        else:
            customer_name = ""
            customer_dob = None

        if m := BOOKED_AT_RE.match(lines[11]):
            booked_at = datetime.datetime(int(m.group("y")), int(m.group("m")), int(m.group("d")), int(m.group("H")), int(m.group("M")), int(m.group("S")))
            booked_at = TZ.localize(booked_at)
        else:
            booked_at = None

        conditions = "\n".join(lines[4:8])

        return ParsedPLAI(
            ticket_type=lines[1],
            valid_from=valid_from,
            valid_to=valid_to,
            conditions=conditions,
            customer_name=customer_name,
            customer_dob=customer_dob,
            booked_at=booked_at,
            tariff=lines[12],
        )
