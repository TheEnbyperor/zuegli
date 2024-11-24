import dataclasses
import typing
from . import layout

@dataclasses.dataclass
class TripPart:
    departure_date: str
    departure_time: str

    arrival_date: str
    arrival_time: str

    departure_station: str
    arrival_station: str


@dataclasses.dataclass
class ParsedRCT2:
    operator_rics: str
    travel_class: str
    trips: typing.List[TripPart]
    document_type: str
    traveller: str
    price: str
    train_data: str
    conditions: str
    extra: str


class RCT2Parser:
    def __init__(self):
        self.contents = [
            [None for _ in range(72)]
            for _ in range(16)
        ]

    def read(self, content: layout.LayoutV1, issuing_rics: typing.Optional[int] = None):
        if issuing_rics in (1184, 1084):
            offset_x = -1
        else:
            offset_x = 0

        for field in content.fields:
            already_new_lined = "\n" in field.text
            x = 0
            y = 0
            for c in field.text:
                if c == "\n":
                    y += 1
                    x = 0
                    continue

                self.contents[y + field.line][x + field.column + offset_x] = c
                x += 1
                if (not already_new_lined) and x == field.width:
                    y += 1
                    x = 0

    def read_area(self, *, top: int, left: int, width: int, height: int) -> typing.List[str]:
        out = []
        for y in range(top, top + height):
            line = ""
            for x in range(left, left + width):
                line += self.contents[y][x] or " "
            out += [line.strip()]

        return out

    def parse(self):
        departure_date_1 =    self.read_area(top=6,  left=1,  width=5,  height=1)[0]
        departure_time_1 =    self.read_area(top=6,  left=7,  width=5,  height=1)[0]
        departure_station_1 = self.read_area(top=6,  left=13, width=21, height=1)[0]
        arrival_station_1 =   self.read_area(top=6,  left=34, width=17, height=1)[0]
        arrival_date_1 =      self.read_area(top=6,  left=52, width=5,  height=1)[0]
        arrival_time_1 =      self.read_area(top=6,  left=58, width=5,  height=1)[0]

        departure_date_2 =    self.read_area(top=7,  left=1,  width=5,  height=1)[0]
        departure_time_2 =    self.read_area(top=7,  left=7,  width=5,  height=1)[0]
        departure_station_2 = self.read_area(top=7,  left=13, width=21, height=1)[0]
        arrival_station_2 =   self.read_area(top=7,  left=34, width=17, height=1)[0]
        arrival_date_2 =      self.read_area(top=7,  left=52, width=5,  height=1)[0]
        arrival_time_2 =      self.read_area(top=7,  left=58, width=5,  height=1)[0]

        travel_class =        self.read_area(top=6,  left=66, width=5,  height=1)[0]

        document_data =       self.read_area(top=0,  left=18, width=34, height=3)
        traveller_data =      self.read_area(top=0,  left=52, width=20, height=3)
        price_data =          self.read_area(top=13, left=52, width=20, height=2)
        train_data =          self.read_area(top=8,  left=0,  width=72, height=4)
        conditions_data =     self.read_area(top=12, left=0,  width=50, height=3)
        operator_rics =       self.read_area(top=2,  left=5,  width=4,  height=1)[0]
        extra_data =          self.read_area(top=3,  left=0,  width=52, height=1)[0]

        trips = []
        if departure_date_1 not in ("", "*") or departure_time_1 not in ("", "*") or \
            arrival_date_1 not in ("", "*") or arrival_time_1 not in ("", "*") or \
            departure_station_1 not in ("", "*") or arrival_station_1 not in ("", "*"):
            trips.append(TripPart(
                departure_date=departure_date_1,
                departure_time=departure_time_1,
                departure_station=departure_station_1,
                arrival_station=arrival_station_1,
                arrival_date=arrival_date_1,
                arrival_time=arrival_time_1,
            ))

        if departure_date_2 not in ("", "*") or departure_time_2 not in ("", "*") or \
            arrival_date_2 not in ("", "*") or arrival_time_2 not in ("", "*") or \
            departure_station_2 not in ("", "*") or arrival_station_2 not in ("", "*"):
            trips.append(TripPart(
                departure_date=departure_date_2,
                departure_time=departure_time_2,
                departure_station=departure_station_2,
                arrival_station=arrival_station_2,
                arrival_date=arrival_date_2,
                arrival_time=arrival_time_2,
            ))

        return ParsedRCT2(
            operator_rics=operator_rics,
            travel_class=travel_class,
            trips=trips,
            document_type="\n".join(document_data).strip(),
            traveller="\n".join(traveller_data).strip(),
            price="\n".join(price_data).strip(),
            train_data="\n".join(train_data).strip(),
            conditions="\n".join(conditions_data).strip(),
            extra=extra_data,
        )