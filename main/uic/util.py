import dataclasses
import datetime
import decimal
import typing

import pytz

class UICException(Exception):
    pass

@dataclasses.dataclass
class Timestamp:
    year: int
    month: int
    day: int
    hour: int
    minute: int
    timezone: str

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d} ({self.timezone})"

    def as_datetime(self):
        tz = pytz.timezone(self.timezone)
        return tz.localize(datetime.datetime(self.year, self.month, self.day, self.hour, self.minute, 0))

    @classmethod
    def from_bytes(cls, data: bytes, rics: typing.Optional[int] = None) -> "Timestamp":
        try:
            timestamp = data.decode("ascii")
            day = int(timestamp[0:2], 10)
            month = int(timestamp[2:4], 10)
            year = int(timestamp[4:8], 10)
            hour = int(timestamp[8:10], 10)
            minute = int(timestamp[10:12], 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise UICException("Invalid UIC ticket timestamp") from e

        if rics in (1084, 1184):
            timezone = "Europe/Amsterdam"
        else:
            timezone = "UTC"

        return cls(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            timezone=timezone,
        )


@dataclasses.dataclass
class Coordinate:
    coordinate_system: str
    longitude: decimal.Decimal
    latitude: decimal.Decimal