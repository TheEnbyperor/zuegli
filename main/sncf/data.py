import dataclasses
import datetime
from . import util

@dataclasses.dataclass
class SNCFTicket:
    pnr: str
    ticket_number: str
    traveler_dob: datetime.date
    traveler_sncf_id: str
    traveler_surname: str
    traveler_forename: str
    tariff_code: str
    travel_date: datetime.date
    travel_class: str
    departure_station: str
    arrival_station: str
    train_number: str
    return_travel_class: str
    return_departure_station: str
    return_arrival_station: str
    return_train_number: str

    @classmethod
    def parse(cls, data: bytes) -> "SNCFTicket":
        try:
            data = data.decode("iso-8859-1")
        except UnicodeDecodeError as e:
            raise util.SNCFException("Invalid ticket encoding") from e

        if len(data) != 131:
            raise util.SNCFException("Invalid ticket length")

        try:
            traveler_dob = datetime.datetime.strptime(data[23:33], "%d/%m/%Y").date()
        except ValueError as e:
            raise util.SNCFException("Invalid date format") from e

        try:
            travel_date = datetime.datetime.strptime(data[48:53], "%d/%m").date()
        except ValueError as e:
            raise util.SNCFException("Invalid date format") from e

        return cls(
            pnr=data[4:10],
            ticket_number=data[10:19],
            traveler_dob=traveler_dob,
            departure_station=data[33:38],
            arrival_station=data[38:43],
            train_number=data[43:48],
            travel_date=travel_date,
            traveler_sncf_id=data[53:72],
            traveler_surname=data[72:91].strip(),
            traveler_forename=data[91:110].strip(),
            travel_class=data[110],
            tariff_code=data[111:115],
            return_travel_class=data[115],
            return_departure_station=data[116:121],
            return_arrival_station=data[121:126],
            return_train_number=data[126:131],
        )