import dataclasses
import typing
import datetime
from . import layout

@dataclasses.dataclass
class TripPart:
    departure: typing.Optional[datetime.datetime]
    departure_date: str
    departure_time: str

    arrival: typing.Optional[datetime.datetime]
    arrival_date: str
    arrival_time: str

    departure_station: str
    arrival_station: str


@dataclasses.dataclass
class ParsedRCT2:
    operator_rics: int
    travel_class: str
    trips: typing.List[TripPart]
    document_type: str
    traveller: str
    price: str
    train_data: str
    conditions: str
    extra: str
    valid_region: str


class RCT2Parser:
    def __init__(self):
        self.contents = [
            [None for _ in range(73)]
            for _ in range(16)
        ]

    def read(self, content: layout.LayoutV1):
        for field in content.fields:
            already_new_lined = "\n" in field.text
            x = 0
            y = 0
            for c in field.text:
                if c == "\n":
                    y += 1
                    x = 0
                    continue

                if y + field.line < 16 and x + field.column < 73:
                    self.contents[y + field.line][x + field.column] = c
                x += 1
                if (not already_new_lined) and x == field.width:
                    y += 1
                    x = 0

    def read_area(self, *, top: int, left: int, width: int, height: int) -> str:
        out = []
        for y in range(top, top + height):
            line = ""
            for x in range(left, left + width):
                line += self.contents[y][x] or " "
            out += [line.strip()]

        return "\n".join(out).strip()

    def parse(self, issuing_rics: typing.Optional[int] = None) -> ParsedRCT2:
        trips = []
        for line in (6, 7):
            departure_dt = None
            arrival_dt = None

            departure_station = self.read_area(top=line, left=12, width=20, height=1)
            arrival_station =   self.read_area(top=line, left=32, width=20, height=1)

            if issuing_rics in (84, 1084, 1184, 3095, 3509, 3606, 3626):
                departure = self.read_area(top=line, left=1,  width=10, height=1)
                arrival =   self.read_area(top=line, left=52, width=10, height=1)

                if departure:
                    departure_dt = datetime.datetime.strptime(departure, "%d%m%y%H%M")
                    departure_date = f"{departure[0:2]}.{departure[2:4]}.{departure[4:6]}"
                    departure_time = f"{departure[6:8]}:{departure[8:10]}"
                else:
                    departure_date = ""
                    departure_time = ""
                if arrival:
                    arrival_dt = datetime.datetime.strptime(arrival, "%d%m%y%H%M")
                    arrival_date = f"{arrival[0:2]}.{arrival[2:4]}.{arrival[4:6]}"
                    arrival_time = f"{arrival[6:8]}:{arrival[8:10]}"
                else:
                    arrival_date = ""
                    arrival_time = ""
            else:
                departure_date = self.read_area(top=line, left=1,  width=5, height=1)
                departure_time = self.read_area(top=line, left=7,  width=5, height=1)
                arrival_date =   self.read_area(top=line, left=52, width=5, height=1)
                arrival_time =   self.read_area(top=line, left=58, width=5, height=1)

            departure_date = departure_date.strip("*-> \r\n")
            departure_time = departure_time.strip("*-> \r\n")
            departure_station = departure_station.strip("*-> \r\n")
            arrival_station = arrival_station.strip("*-> \r\n")
            arrival_date = arrival_date.strip("*-> \r\n")
            arrival_time = arrival_time.strip("*-> \r\n")

            if departure_date or departure_time or arrival_date or arrival_time or departure_station or arrival_station:
                trips.append(TripPart(
                    departure_date=departure_date,
                    departure_time=departure_time,
                    departure_station=departure_station,
                    arrival_station=arrival_station,
                    arrival_date=arrival_date,
                    arrival_time=arrival_time,
                    departure=departure_dt,
                    arrival=arrival_dt,
                ))

        travel_class =        self.read_area(top=6,  left=65, width=8,  height=1).strip("*- \r\n")
        document_data =       self.read_area(top=0,  left=12, width=40, height=3).strip("*- \r\n")
        traveller_data =      self.read_area(top=0,  left=52, width=20, height=3).strip("*- \r\n")
        price_data =          self.read_area(top=13, left=52, width=20, height=2).strip("*- \r\n")
        train_data =          self.read_area(top=8,  left=0,  width=72, height=4).strip("*- \r\n")
        valid_region =        self.read_area(top=8,  left=0,  width=72, height=1).strip("*- \r\n")
        conditions_data =     self.read_area(top=12, left=0,  width=50, height=3).strip("*- \r\n")
        operator_rics =       self.read_area(top=2,  left=5,  width=4,  height=1).lstrip(" 0").rstrip(" ")

        try:
            operator_rics = int(operator_rics, 10)
        except ValueError:
            operator_rics = 0
        extra_data =          self.read_area(top=3,  left=0,  width=52, height=1)

        if operator_rics in (1088, 1184):
            # BeNeRail (NSI and SNCB/NMBS International) uses square brackets in the via-string where chevrons should be used
            valid_region = valid_region.replace("[", "<").replace("]", ">")

        return ParsedRCT2(
            operator_rics=operator_rics,
            travel_class=travel_class,
            trips=trips,
            document_type=document_data,
            traveller=traveller_data,
            price=price_data,
            train_data=train_data,
            conditions=conditions_data,
            extra=extra_data,
            valid_region = valid_region,
        )