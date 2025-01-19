import dataclasses
import typing
import datetime
import json
import pytz


class OeBBException(Exception):
    pass

@dataclasses.dataclass
class Train:
    train_number: str
    carriage_number: str

@dataclasses.dataclass
class OeBBRecord99:
    validity_start: datetime.datetime
    validity_end: datetime.datetime
    trains: typing.List[Train]

    @classmethod
    def parse(cls, data: bytes, version: int):
        if version != 1:
            raise OeBBException(f"Unsupported record version {version}")

        tz = pytz.UTC

        try:
            data = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise OeBBException(f"Invalid OeBB 99 record") from e

        validity_start = data.pop("V")
        validity_end = data.pop("B")
        trains = []

        if "Z" in data:
            for t in data.pop("Z").split(";"):
                d = t.split(":", 2)
                train_number = d[0]
                if len(d) > 1:
                    carriage_number = d[1]
                else:
                    carriage_number = None
                trains.append(Train(train_number, carriage_number))

        validity_start = tz.localize(datetime.datetime.strptime(validity_start, "%y%m%d%H%M"))
        validity_end = tz.localize(datetime.datetime.strptime(validity_end, "%y%m%d%H%M"))

        return cls(
            validity_start=validity_start,
            validity_end=validity_end,
            trains=trains,
        )