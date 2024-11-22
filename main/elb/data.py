import dataclasses
import datetime
import pytz
from django.utils import timezone
from . import util

TZ = pytz.timezone('Europe/Paris')

@dataclasses.dataclass
class ELBTicket:
    code_pectab: str
    ticket_code: str
    pnr: str
    booking_number: str
    specimen: bool
    version_number: str
    sequence_number: int
    total_tickets: int
    traveler_type: str
    number_adults: int
    number_children: int
    emission: datetime.date
    valid_from: datetime.date
    valid_until: datetime.date
    departure_station: str
    arrival_station: str
    train_number: str
    security_number: str
    departure_date: datetime.date
    coach_number: str
    seat_number: str
    travel_class: str
    tariff_code: str

    @classmethod
    def parse(cls, data: bytes) -> "ELBTicket":
        try:
            data = data.decode("iso-8859-1")
        except UnicodeDecodeError as e:
            raise util.ELBException("Invalid ticket encoding") from e

        if data[0] != "e":
            raise util.ELBException("Not an ELB ticket")

        if data[19] == "1":
            specimen = False
        elif data[19] == "0":
            specimen = True
        else:
            raise util.ELBException("Invalid specimen flag")

        try:
            sequence_number = int(data[21])
        except ValueError as e:
            raise util.ELBException("Invalid sequence number") from e

        try:
            total_tickets = int(data[22])
        except ValueError as e:
            raise util.ELBException("Invalid total tickets count") from e

        try:
            number_adults = int(data[35:37])
        except ValueError as e:
            raise util.ELBException("Invalid number adults") from e

        try:
            number_children = int(data[37:39])
        except ValueError as e:
            raise util.ELBException("Invalid number children") from e

        try:
            year = int(data[39])
        except ValueError as e:
            raise util.ELBException("Invalid year") from e

        try:
            emission_day = int(data[40:43])
        except ValueError as e:
            raise util.ELBException("Invalid emission day") from e

        try:
            begin_validity_day = int(data[43:46])
        except ValueError as e:
            raise util.ELBException("Invalid begin validity day") from e

        try:
            end_validity_day = int(data[46:49])
        except ValueError as e:
            raise util.ELBException("Invalid end validity day") from e

        try:
            departure_day = int(data[69:72])
        except ValueError as e:
            raise util.ELBException("Invalid departure day") from e

        now = timezone.now()
        year = ((now.year // 10) * 10) + year
        year_start = datetime.date(year, 1, 1)
        emission = year_start + datetime.timedelta(days=emission_day - 1)
        valid_from = year_start + datetime.timedelta(days=begin_validity_day - 1)
        valid_until = year_start + datetime.timedelta(days=end_validity_day - 1)
        departure_date = year_start + datetime.timedelta(days=departure_day - 1)

        if valid_from < emission:
            valid_from = valid_from.replace(year=valid_from.year + 1)
        if valid_until < emission:
            valid_until = valid_until.replace(year=valid_until.year + 1)
        if departure_date < valid_from:
            departure_date = departure_date.replace(year=departure_date.year + 1)

        return cls(
            code_pectab=data[1],
            ticket_code=data[2:3],
            pnr=data[4:10],
            booking_number=data[10:19],
            specimen=specimen,
            version_number=data[20],
            sequence_number=sequence_number,
            total_tickets=total_tickets,
            traveler_type=data[33:35],
            number_adults=number_adults,
            number_children=number_children,
            emission=emission,
            valid_from=valid_from,
            valid_until=valid_until,
            departure_station=data[49:54].strip(),
            arrival_station=data[54:59].strip(),
            train_number=data[59:65].strip(" 0"),
            security_number=data[65:69],
            departure_date=departure_date,
            coach_number=data[72:75].strip(" 0"),
            seat_number=data[75:78].strip(" 0"),
            travel_class=data[78],
            tariff_code=data[79:82].strip(),
        )

    def validity_start_time(self) -> datetime.datetime:
        return TZ.localize(datetime.datetime.combine(self.valid_from, datetime.time.min))

    def validity_end_time(self) -> datetime.datetime:
        return TZ.localize(datetime.datetime.combine(self.valid_until, datetime.time.max))

    def departure_time(self) -> datetime.datetime:
        return TZ.localize(datetime.datetime.combine(self.departure_date, datetime.time.min))