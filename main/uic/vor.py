import dataclasses
import re
import datetime
import pytz
import enum
import typing

TZ = pytz.timezone("Europe/Vienna")

class VORException(Exception):
    pass

class Gender(enum.Enum):
    Male = 1
    Female = 2
    Diverse = 3

@dataclasses.dataclass
class VORRecordFI:
    validity_start: datetime.datetime
    validity_end: typing.Optional[datetime.datetime]
    raw_data: str

    @classmethod
    def parse(cls, data: bytes, version: int):
        if version != 1:
            raise VORException(f"Unsupported FI record version {version}")

        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise VORException("Invalid FI record text encoding") from e

        if len(data) < 55:
            raise VORException("FI record is too short")

        validity_start_str = data[0:16]
        validity_end_str = data[16:32]

        try:
            validity_start = TZ.localize(datetime.datetime.strptime(validity_start_str, "%d.%m.%Y %H:%M")) \
                .astimezone(tz=pytz.UTC)
        except ValueError as e:
            raise VORException(f"Invalid validity start date") from e

        if validity_end_str.strip():
            try:
                validity_end = TZ.localize(datetime.datetime.strptime(validity_end_str, "%d.%m.%Y %H:%M")) \
                    .astimezone(tz=pytz.UTC)
            except ValueError as e:
                raise VORException(f"Invalid validity end date") from e
        else:
            validity_end = None

        return cls(
            validity_start=validity_start,
            validity_end=validity_end,
            raw_data=data,
        )


@dataclasses.dataclass
class VORRecordVD:
    raw_data: str
    customer_id: str
    date_of_birth: typing.Optional[datetime.date]
    gender: typing.Optional[Gender]
    title: typing.Optional[str] = None
    forename: typing.Optional[str] = None
    middle_name: typing.Optional[str] = None
    surname: typing.Optional[str] = None
    suffix: typing.Optional[str] = None

    @classmethod
    def parse(cls, data: bytes, version: int):
        if version != 1:
            raise VORException(f"Unsupported VD record version {version}")

        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise VORException("Invalid VD record text encoding") from e

        if len(data) < 69:
            raise VORException("Invalid VD record length")

        customer_id = data[:48].strip()
        gender_str = data[48]
        dob_str = data[49:57]
        name_str = data[69:]

        if dob_str.strip():
            try:
                dob = datetime.datetime.strptime(dob_str, "%d%m%Y").date()
            except ValueError as e:
                raise VORException("Invalid date of birth") from e
        else:
            dob = None

        title = None
        forename = None
        middle_name = None
        surname = None
        suffix = None

        if name_str:
            name_parts = name_str.split("|")
            if len(name_parts) != 5:
                raise VORException("Invalid VD record name - unexpected number of parts")

            title = name_parts[0]
            forename = name_parts[1]
            middle_name = name_parts[2]
            surname = name_parts[3]
            suffix = name_parts[4]

        if gender_str == "M":
            gender = Gender.Male
        elif gender_str == "W":
            gender = Gender.Female
        elif gender_str == "D":
            gender = Gender.Diverse
        elif gender_str == " ":
            gender = None
        else:
            raise VORException(f"Unknown gender {gender_str}")

        return cls(
            customer_id=customer_id,
            date_of_birth=dob,
            title=title,
            forename=forename,
            middle_name=middle_name,
            surname=surname,
            suffix=suffix,
            gender=gender,
            raw_data=data,
        )
