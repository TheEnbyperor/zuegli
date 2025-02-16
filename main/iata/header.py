import dataclasses
from . import util

@dataclasses.dataclass
class Header:
    passenger_surname: str
    passenger_forename: str
    electronic_ticket_indicator: str

    @classmethod
    def parse(cls, data: str) -> "Header":
        if len(data) != 21:
            raise util.IATAException("Header data must be 21 characters long")

        passenger_name = data[:20].split("/", 1)
        passenger_surname = passenger_name[0].rstrip()
        passenger_forename = passenger_name[1].rstrip() if len(passenger_name) > 1 else ""
        electronic_ticket_indicator = data[20].strip()

        return cls(
            passenger_surname=passenger_surname,
            passenger_forename=passenger_forename,
            electronic_ticket_indicator=electronic_ticket_indicator
        )
