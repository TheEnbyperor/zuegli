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
    track_code: str
    zone_start: int
    zone_end: int
    zone_via_1: int
    zone_via_2: int
    reference_id: typing.Optional[str]

    @classmethod
    def parse(cls, data: bytes, version: int):
        if version != 1:
            raise VORException(f"Unsupported VOR FI record version {version}")

        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise VORException("Invalid VOR FI record text encoding") from e

        if len(data) != 75:
            raise VORException("VOR FI record wrong length")

        validity_start_str = data[0:16]
        validity_end_str = data[16:32]
        track_code = data[32:35]
        zone_start = data[35:40]
        zone_end = data[40:45]
        zone_via_1 = data[45:50]
        zone_via_2 = data[50:55]
        reference_id = data[55:75]

        try:
            validity_start = TZ.localize(datetime.datetime.strptime(validity_start_str, "%d.%m.%Y %H:%M"))
        except ValueError as e:
            raise VORException(f"Invalid validity start date") from e

        if validity_end_str.strip():
            try:
                validity_end = TZ.localize(datetime.datetime.strptime(validity_end_str, "%d.%m.%Y %H:%M"))
            except ValueError as e:
                raise VORException(f"Invalid validity end date") from e
        else:
            validity_end = None

        try:
            zone_start = int(zone_start, 10)
            zone_end = int(zone_end, 10)
            zone_via_1 = int(zone_via_1, 10)
            zone_via_2 = int(zone_via_2, 10)
        except ValueError as e:
            raise VORException("Invalid VOR FI record zone number") from e

        reference_id = reference_id.strip()
        reference_id = reference_id if reference_id else None

        o = cls(
            validity_start=validity_start,
            validity_end=validity_end,
            track_code=track_code.strip(),
            zone_start=zone_start,
            zone_end=zone_end,
            zone_via_1=zone_via_1,
            zone_via_2=zone_via_2,
            reference_id=reference_id,
        )
        return o


@dataclasses.dataclass
class VORRecordVD:
    contract_id: typing.Optional[str]
    customer_id: typing.Optional[str]
    date_of_birth: typing.Optional[datetime.date]
    gender: typing.Optional[Gender]
    id_document_type: typing.Optional[str]
    id_document_number: typing.Optional[str]
    title: typing.Optional[str] = None
    forename: typing.Optional[str] = None
    middle_name: typing.Optional[str] = None
    surname: typing.Optional[str] = None
    suffix: typing.Optional[str] = None

    @classmethod
    def parse(cls, data: bytes, version: int):
        if version != 1:
            raise VORException(f"Unsupported VOR VD record version {version}")

        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise VORException("Invalid VOR VD record text encoding") from e

        if len(data) < 69:
            raise VORException("Invalid VOR VD record length")

        contract_id = data[0:30]
        customer_id = data[30:48]
        gender_str = data[48]
        dob_str = data[49:57]
        id_document_type = data[57:59]
        id_document_number = data[59:69]
        name_str = data[69:]

        contract_id = contract_id.strip()
        contract_id = contract_id if contract_id else None
        customer_id = customer_id.strip()
        customer_id = customer_id if customer_id else None
        id_document_type = id_document_type.strip()
        id_document_type = id_document_type if id_document_type else None
        id_document_number = id_document_number.strip()
        id_document_number = id_document_number if id_document_number else None

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
            contract_id=contract_id,
            customer_id=customer_id,
            date_of_birth=dob,
            id_document_type=id_document_type,
            id_document_number=id_document_number,
            title=title,
            forename=forename,
            middle_name=middle_name,
            surname=surname,
            suffix=suffix,
            gender=gender,
        )


@dataclasses.dataclass
class VORProduct:
    product_id: int
    product_code: str
    count: int

@dataclasses.dataclass
class VORRecordFK:
    currency: str
    partner_id: typing.Optional[str]
    products: typing.List[VORProduct]

    @classmethod
    def parse(cls, data: bytes, version: int):
        if version != 1:
            raise VORException(f"Unsupported VOR FK record version {version}")

        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise VORException("Invalid VOR FK record text encoding") from e

        if len(data) < 13:
            raise VORException("Invalid VOR FK record length")

        currency = data[0:3]
        partner_id = data[3:13]

        partner_id = partner_id.strip()
        partner_id = partner_id if partner_id else None

        products = []
        for d in (data[i:i+9] for i in range(13, len(data), 9)):
            product_id = d[0:5].strip()
            if product_id:
                try:
                    product_id = int(product_id, 10)
                except ValueError as e:
                    raise VORException("Invalid VOR product ID") from e
            else:
                product_id = 0
            try:
                count = int(d[6:9], 10)
            except ValueError as e:
                raise VORException("Invalid VOR product count") from e
            products.append(VORProduct(
                product_id=product_id,
                product_code=d[5],
                count=count,
            ))

        return cls(
            currency=data[0:3],
            partner_id=partner_id,
            products=products,
        )
