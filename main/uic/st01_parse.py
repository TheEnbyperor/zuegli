import dataclasses
import typing
import datetime
from . import layout


@dataclasses.dataclass
class ParsedST01:
    ticket_id: str
    ticket_type: str
    validity: str
    valid_from: typing.Optional[datetime.date]
    valid_to: typing.Optional[datetime.date]
    passenger_name: str
    passenger_dob: typing.Optional[datetime.date]


class ST01Parser:
    def __init__(self):
        self.lines = []

    def read(self, content: layout.LayoutV1):
        self.lines = [""] * (max(map(lambda f: f.line, content.fields)) + 1)
        for field in content.fields:
            if field.column != 1 or field.height != 1:
                continue
            self.lines[field.line] = field.text

    def parse(self) -> ParsedST01:
        return ParsedST01(
            ticket_id=self.lines[0] if len(self.lines) > 0 else "",
            ticket_type=self.lines[1] if len(self.lines) > 1 else "",
            validity=self.lines[4] if len(self.lines) > 4 else "",
            valid_from=datetime.datetime.strptime(self.lines[7], "%d.%m.%Y").date() if len(self.lines) > 7 and self.lines[7] else None,
            valid_to=datetime.datetime.strptime(self.lines[8], "%d.%m.%Y").date() if len(self.lines) > 8 and self.lines[8] else None,
            passenger_name=self.lines[9] if len(self.lines) > 9 else "",
            passenger_dob=datetime.datetime.strptime(self.lines[6], "%Y-%m-%d").date() if len(self.lines) > 6 and self.lines[6] else None,
        )
