import dataclasses
import datetime
from django.utils import timezone
from . import util

@dataclasses.dataclass
class Keycard:
    version: int
    card_id: str
    number_adults: int
    number_children: int
    specimen: bool
    travel_class: int
    extra_text: str
    station_uic: int
    issuing_date: datetime.date
    validity_start: datetime.date
    validity_end: datetime.date
    num_travel_days: int
    product_code: int

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
            number_adults=data.read_int(0, 7),
            number_children=data.read_int(7, 14),
            specimen=not data.read_bool(14),
            travel_class=data.read_int(15, 21),
            card_id=data.read_string(21, 105),
            issuing_date=issuing_date,
            product_code=data.read_int(118, 125),
            version=data.read_int(125, 129),
            validity_start=validity_start,
            validity_end=validity_end,
            num_travel_days=data.read_int(150, 157),
            extra_text=data.read_string(157, 367),
            station_uic=8400000 + station_id if station_id else 0,
            # 384 - 463 UNKNOWN
        )

    @property
    def product_name(self):
        if self.product_code == 1:
            return "Keycard"
        elif self.product_code == 2:
            return "Jaarpas passage"
        elif self.product_code == 3:
            return "Kwartlalpas passage"
        elif self.product_code == 4:
            return "Dagpas"
        elif self.product_code == 5:
            return "Dagpas groep"
        elif self.product_code == 6:
            return "Preprinted ATB"
        elif self.product_code == 7:
            return "Uitstel van Betaling"
        elif self.product_code == 8:
            return "Meereiskaart Spoordeelweken"
        elif self.product_code == 9:
            return "Landencoupon"
        elif self.product_code == 12:
            return "Thalys Employee Pass"
        elif self.product_code == 14:
            return "Eurail Pass Cover"
        elif self.product_code == 15:
            return "Interrail Pass Cover"
        elif self.product_code == 16:
            return "Boekenweekgeschenk"
        elif self.product_code == 17:
            return "Dagpas Speciaal"
        elif self.product_code == 18:
            return "Keycard Speciaal"
        elif self.product_code == 19:
            return "Weekend passage"
        elif self.product_code == 20:
            return "Charter Dagpas RPR"
        elif self.product_code == 21:
            return "NMBS Trainkaarten"
        elif self.product_code == 20:
            return "NMBS Internet Uitgifte"
        elif self.product_code == 25:
            return "Exit recht"
        elif self.product_code == 26:
            return "Evenement"
        elif self.product_code == 27:
            return "Maandpas passage"
        elif self.product_code == 28:
            return "Halfjaarpas passage"
        elif self.product_code == 29:
            return "Dagpas groep (dynamisch)"
        elif self.product_code == 30:
            return "Weekpas"
        elif self.product_code == 33:
            return "Dagpas avond"
        else:
            return f"Unknown - {self.product_code}"