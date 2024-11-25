import dataclasses
import datetime
from django.utils import timezone
from . import util

@dataclasses.dataclass
class Keycard:
    card_id: str
    extra_text: str
    station_uic: int
    issuing_date: datetime.date
    validity_start: datetime.date
    validity_end: datetime.date

    @staticmethod
    def type():
        return "NS_KC"

    @property
    def pnr(self):
        return self.card_id

    @classmethod
    def parse(cls, data: util.BitStream):
        year = data.read_int(105, 109)
        issuing_day = data.read_int(109, 118)
        validity_start_day = data.read_int(129, 138)
        validity_end_day = data.read_int(138, 150)

        now = timezone.now()
        year = ((now.year // 10) * 10) + year
        year_start = datetime.date(year, 1, 1)
        if year_start > now.date():
            year_start = year_start.replace(year=year_start.year - 10)
        issuing_date = year_start + datetime.timedelta(days=issuing_day - 1)
        validity_start = issuing_date + datetime.timedelta(days=validity_start_day)
        validity_end = issuing_date + datetime.timedelta(days=validity_end_day)

        station_id = data.read_int(367, 384)

        return cls(
            # 0 - 20 UNKNOWN
            card_id=data.read_string(21, 105),
            issuing_date=issuing_date,
            # 118 - 128 UNKNOWN
            validity_start=validity_start,
            validity_end=validity_end,
            # 150 UNKNOWN
            extra_text=data.read_string(151, 367),
            station_uic=8400000 + station_id if station_id else 0,
            # 384 - 463 UNKNOWN
        )