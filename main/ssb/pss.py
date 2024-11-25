import dataclasses
import datetime
import typing
from django.utils import timezone
from . import util

@dataclasses.dataclass
class Pass:
    specimen: bool
    num_adults: int
    num_children: int
    travel_class: int
    pnr: str
    issuing_date: datetime.date
    sub_type: int
    validity_start: datetime.date
    validity_end: datetime.date
    travel_days: int
    countries: typing.List[int]
    two_pages: bool
    information_message: int
    extra_text: str

    @staticmethod
    def type():
        return "PASS"

    @classmethod
    def parse(cls, data: util.BitStream):
        year = data.read_int(105, 109)
        issuing_day = data.read_int(109, 118)
        first_day = data.read_int(120, 129)
        last_day = data.read_int(129, 138)

        now = timezone.now()
        year = ((now.year // 10) * 10) + year
        year_start = datetime.date(year, 1, 1)
        if year_start > now.date():
            year_start = year_start.replace(year=year_start.year - 10)
        issuing_date = year_start + datetime.timedelta(days=issuing_day - 1)
        validity_start = issuing_date + datetime.timedelta(days=first_day)
        validity_end = issuing_date + datetime.timedelta(days=last_day)

        countries = [data.read_int(145, 152)]
        if c := data.read_int(152, 159):
            countries.append(c)
        if c := data.read_int(159, 166):
            countries.append(c)
        if c := data.read_int(166, 173):
            countries.append(c)
        if c := data.read_int(173, 180):
            countries.append(c)

        return cls(
            specimen=data.read_bool(14),
            num_adults=data.read_int(0, 7),
            num_children=data.read_int(7, 14),
            travel_class=data.read_int(15, 21),
            pnr=data.read_string(21, 105),
            issuing_date=issuing_date,
            sub_type=data.read_int(118, 120),
            validity_start=validity_start,
            validity_end=validity_end,
            travel_days=data.read_int(138, 145),
            countries=countries,
            two_pages=data.read_bool(180),
            information_message=data.read_int(181, 195),
            extra_text=data.read_string(195, 435),
        )