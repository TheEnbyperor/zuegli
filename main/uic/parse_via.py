import enum
import typing
import uuid
import json
import pathlib
import dataclasses
from . import rics, stations

DB_ABBR = None
ROOT_DIR = pathlib.Path(__file__).parent


def get_db_abbr():
    global DB_ABBR

    if DB_ABBR:
        return DB_ABBR

    with open(ROOT_DIR / "data" / "db-leitpunktkuerzel.json") as f:
        DB_ABBR = json.load(f)

    return DB_ABBR


class Point:
    def __init__(self, name: str):
        self.name = name.strip()
        self.id = uuid.uuid4()

class List:
    def __init__(self):
        self.points = []

    def append(self, point):
        self.points.append(point)

    def __iter__(self):
        return iter(self.points)

class Options:
    def __init__(self):
        self.choices = []

    def append(self, options: List):
        self.choices.append(options)

class Carrier:
    def __init__(self, carrier_num: str, points: List):
        self.carrier_nums = carrier_num.split(",")
        self.points = points
        self.id = uuid.uuid4()

        if not self.points.points:
            self.points.append(Point('ANY'))


class Route:
    def __init__(self):
        self.carriers = []
        self.out = []
        self.edges = []

    def append(self, carrier: Carrier):
        self.carriers.append(carrier)

    def _print_point(self, point: Point) -> typing.Tuple[typing.List[str], typing.List[str]]:
        point_id = f"point_{point.id.hex}"
        db_abbr = get_db_abbr()
        if point.name in db_abbr:
            self.out.append(f"{point_id} [label=\"{db_abbr[point.name]['name']}\", shape=\"box\", style=\"rounded\"]")
        else:
            self.out.append(f"{point_id} [label=\"{point.name}\", shape=\"box\", style=\"rounded\"]")
        return [point_id], [point_id]

    def _print_options(self, options: Options) -> typing.Tuple[typing.List[str], typing.List[str]]:
        entry_points = []
        exit_points = []
        for option in options.choices:
            entry_point, exit_point = self._print_list(option)
            entry_points.extend(entry_point)
            exit_points.extend(exit_point)
        return entry_points, exit_points

    def _print_list(self, l: List) -> typing.Tuple[typing.List[str], typing.List[str]]:
        def print_item(item):
            if isinstance(item, Point):
                return self._print_point(item)
            elif isinstance(item, Options):
                return self._print_options(item)

        point_ids = list(map(print_item, l))
        for i, ee in enumerate(point_ids[:-1]):
            for exit_point in ee[1]:
                for entry_point in point_ids[i+1][0]:
                    self.edges.append(f"{exit_point} -> {entry_point}")
        return point_ids[0][0], point_ids[-1][1]

    def to_graph(self):
        self.out = []
        self.edges = []
        self.out.append("digraph {")
        self.out.append("rankdir=\"LR\";")
        self.out.append("start [label=\"Start\"]")
        exit_points = ["start"]
        for carrier in self.carriers:
            self.out.append(f"subgraph cluster_{carrier.id.hex} {{")
            carrier_names = []
            for n in carrier.carrier_nums:
                if c := rics.get_rics(n):
                    carrier_names.append(c["full_name"].replace("/", "\\n"))
                else:
                    carrier_names.append(n)
            carrier_names = ", ".join(carrier_names)
            self.out.append(f"label=\"{carrier_names}\"")
            prev_exit_points = exit_points
            entry_points, exit_points = self._print_list(carrier.points)
            for exit_point in prev_exit_points:
                for entry_point in entry_points:
                    self.edges.append(f"{exit_point} -> {entry_point}")
            self.out.append("}")
        self.out.append("end [label=\"End\"]")
        for p in exit_points:
            self.edges.append(f"{p} -> end")
        self.out.extend(self.edges)
        self.out.append("}")
        return "\n".join(self.out)


class State(enum.Enum):
    START = 0
    CARRIER = 1
    POINTS = 2

class StringReader:
    def __init__(self, val):
        self.data = val
        self.pos = 0
        self.peek_pos = 0

    def eof(self):
        return self.pos >= len(self.data)

    def read(self):
        c = self.data[self.pos]
        self.pos += 1
        self.peek_pos = 0
        return c

    def peek(self):
        c = self.data[self.pos + self.peek_pos]
        self.peek_pos += 1
        return c

def parse_via(via: str) -> Route:
    reader = StringReader(via)
    state = State.START

    carrier_num = ""
    route = Route()
    point = ""
    points = List()
    point_stack = []
    seen_slash_stack = []
    options_stack = []

    while not reader.eof():
        if state == State.START:
            c = reader.read()
            if c == "<":
                state = State.CARRIER
                carrier_num = ""
                point = ""
            elif c.upper() == "V":
                if reader.peek().upper() == "I" and reader.peek().upper() == "A" and reader.peek() == ":":
                    reader.read()
                    reader.read()
                    reader.read()
                    state = State.POINTS
                    carrier_num = ""
                    point = ""
        elif state == State.CARRIER:
            c = reader.read()
            if c == ">":
                state = State.POINTS
            else:
                carrier_num += c
        elif state == State.POINTS:
            c = reader.read()
            if c == "*":
                if point:
                    points.append(Point(point))
                point = ""
            elif c == "(":
                depth = 0
                seen_slash = False
                while True:
                    c = reader.peek()
                    if depth == 0:
                        if c == ")":
                            break
                        elif c == "/":
                            seen_slash = True
                    else:
                        if c == "(":
                            depth += 1
                        elif c == ")":
                            depth -= 1

                seen_slash_stack.append(seen_slash)
                if seen_slash:
                    point_stack.append(points)
                    options_stack.append(Options())
                    points = List()
                    point = ""
                else:
                    point += "("
            elif c == "/" and seen_slash_stack:
                points.append(Point(point))
                point = ""
                options_stack[-1].append(points)
                points = List()
            elif c == ")":
                if seen_slash_stack.pop():
                    points.append(Point(point))
                    options_stack[-1].append(points)
                    points = point_stack.pop()
                    points.append(options_stack.pop())
                    point = ""
                else:
                    point += ")"
            elif c == "<":
                points.append(Point(point))
                if carrier_num or any(
                        isinstance(p, Options) or
                        (isinstance(p, Point) and p.name)
                        for p in points
                ):
                    route.append(Carrier(carrier_num, points))
                state = State.CARRIER
                carrier_num = ""
                point = ""
                points = List()
                point_stack = []
                seen_slash_stack = []
                options_stack = []
            else:
                point += c

    if point:
        points.append(Point(point))

    if carrier_num or any(
            isinstance(p, Options) or
            (isinstance(p, Point) and p.name)
            for p in points
    ):
        route.append(Carrier(carrier_num, points))

    return route

@dataclasses.dataclass(frozen=True)
class FlexCarrier:
    rics: typing.FrozenSet[int]
    name: typing.FrozenSet[str]

@dataclasses.dataclass(frozen=True)
class FlexStation:
    code_table: str
    code: int
    name: str
    carrier: typing.Optional[int]

class FlexVia:
    carriers: typing.Set[FlexCarrier]
    stations: typing.Set[FlexStation]
    edges: typing.Dict[int, typing.List[int]]

    def __init__(self):
        self.carriers = set()
        self.stations = set()
        self.edges = {}

    @classmethod
    def parse(cls, via: dict) -> "FlexVia":
        out = cls()
        d = out.parse_(via, [1])
        out.add_edges(d, [2])
        return out

    def parse_(self, via: dict, origin: typing.List[int], current_carrier: typing.Optional["FlexCarrier"] = None):
        if "carrierNum" in via or "carrierIA5" in via:
            current_carrier = FlexCarrier(frozenset(via.get("carrierNum", [])), frozenset(via.get("carrierIA5", [])))
            self.carriers.add(current_carrier)

        if "stationNum" in via or "stationIA5" in via:
            station = FlexStation(
                code_table=via.get("stationCodeTable"),
                code=via.get("stationNum"),
                name=via.get("stationIA5"),
                carrier=hash(current_carrier) if current_carrier else None,
            )
            self.stations.add(station)
            d = [hash(station)]
            self.add_edges(origin, d)
            return d
        elif "route" in via:
            for v in via["route"]:
                origin = self.parse_(v, origin, current_carrier)
            return origin
        elif "alternativeRoutes" in via:
            d = []
            for a in via["alternativeRoutes"]:
                d.extend(self.parse_(a, origin, current_carrier))
            return d
        else:
            return []

    def add_edges(self, origin: typing.List[int], destination: typing.List[int]):
        for d in destination:
            for o in origin:
                if o in self.edges:
                    self.edges[o].append(d)
                else:
                    self.edges[o] = [d]

    def _add_station(self, station: FlexStation):
        label = None
        if station.code and station.code_table == "stationUIC":
            if s := stations.get_station_by_uic(station.code):
                label = s["name"]
        if not label:
            if station.name:
                label = station.name
            else:
                label = str(station.code)

        self.out.append(f"station_{hex(abs(hash(station)))} [label=\"{label}\", shape=\"box\", style=\"rounded\"]")

    def to_graph(self):
        self.out = []
        self.out.append("digraph {")
        self.out.append("rankdir=\"LR\";")
        self.out.append("start [label=\"Start\"]")

        for carrier in self.carriers:
            ch = hash(carrier)
            self.out.append(f"subgraph cluster_{hex(abs(ch))} {{")
            carrier_names = []
            for n in carrier.rics:
                if c := rics.get_rics(n):
                    carrier_names.append(c["full_name"])
                else:
                    carrier_names.append(n)
            carrier_names = ", ".join(carrier_names)
            self.out.append(f"label=\"{carrier_names}\"")

            for station in self.stations:
                if station.carrier == ch:
                    self._add_station(station)

            self.out.append("}")

        for station in self.stations:
            if station.carrier is None:
                self._add_station(station)

        self.out.append("end [label=\"End\"]")

        for o, ds in self.edges.items():
            if o == 1:
                o_name = "start"
            elif o == 2:
                o_name = "end"
            else:
                o_name = f"station_{hex(abs(o))}"
            for d in ds:
                if d == 1:
                    d_name = "start"
                elif d == 2:
                    d_name = "end"
                else:
                    d_name = f"station_{hex(abs(d))}"
                self.out.append(f"{o_name} -> {d_name}")

        self.out.append("}")
        return "\n".join(self.out)
