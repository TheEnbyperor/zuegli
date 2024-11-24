import enum
import typing
import uuid
import json
import pathlib
from . import rics

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
        self.name = name
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
        self.carrier_num = carrier_num
        self.points = points
        self.id = uuid.uuid4()

        if not self.points.points:
            self.points.append(Point('ANY'))


class Route:
    def __init__(self):
        self.carriers = []
        self.out = []

    def append(self, carrier: Carrier):
        self.carriers.append(carrier)

    def _print_point(self, point: Point) -> typing.Tuple[typing.List[str], typing.List[str]]:
        point_id = f"point_{point.id.hex}"
        db_abbr = get_db_abbr()
        if point.name in db_abbr:
            self.out.append(f"{point_id} [label=\"{db_abbr[point.name]['name']}\", shape=\"plain\"]")
        else:
            self.out.append(f"{point_id} [label=\"{point.name}\", shape=\"plain\"]")
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
                    self.out.append(f"{exit_point} -> {entry_point}")
        return point_ids[0][0], point_ids[-1][1]

    def to_graph(self):
        self.out = []
        self.out.append("digraph {")
        self.out.append("rankdir=\"LR\";")
        self.out.append("start [label=\"Start\"]")
        exit_points = ["start"]
        for carrier in self.carriers:
            self.out.append(f"subgraph cluster_{carrier.id.hex} {{")
            if c := rics.get_rics(carrier.carrier_num):
                self.out.append(f"label=\"{c['full_name']}\"")
            else:
                self.out.append(f"label=\"{carrier.carrier_num}\"")
            prev_exit_points = exit_points
            entry_points, exit_points = self._print_list(carrier.points)
            for exit_point in prev_exit_points:
                for entry_point in entry_points:
                    self.out.append(f"{exit_point} -> {entry_point}")
            self.out.append("}")
        self.out.append("end [label=\"End\"]")
        for p in exit_points:
            self.out.append(f"{p} -> end")
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
            if reader.read() == "<":
                state = State.CARRIER
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

    route.append(Carrier(carrier_num, points))

    return route
