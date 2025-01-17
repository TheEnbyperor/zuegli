import dataclasses
import typing
import datetime
import json
import pytz


class OeBBException(Exception):
    pass

@dataclasses.dataclass
class OeBBRecord99:
    validity_start: datetime.datetime
    validity_end: datetime.datetime
    train_number: typing.Optional[str]
    carriage_number: typing.Optional[str]

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
        train_number = None
        carriage_number = None

        if "Z" in data:
            d = data.pop("Z").split(":", 2)
            train_number = d[0]
            if len(d) > 1:
                carriage_number = d[1]

        validity_start = tz.localize(datetime.datetime.strptime(validity_start, "%y%m%d%H%M"))\
            .astimezone(tz=pytz.UTC)
        validity_end = tz.localize(datetime.datetime.strptime(validity_end, "%y%m%d%H%M"))\
            .astimezone(tz=pytz.UTC)

        return cls(
            validity_start=validity_start,
            validity_end=validity_end,
            train_number=train_number,
            carriage_number=carriage_number,
        )