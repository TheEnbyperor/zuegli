import dataclasses
import datetime
import pytz

TAG_OCTET_STRING = 0x04
TAG_NULL = 0x05
TAG_OID = 0x06
TAG_SEQUENCE = 0x30
TAG_SIGNATURE = 0x9E
REMAINING_DATA = 0x9A
TAG_CA_REFERENCE = 0x42
TAG_TICKET_PRODUCT_DATA = 0x85
TAG_TICKET_PRODUCT_TRANSACTION_DATA = 0x8A
TAG_CERTIFICATE = 0x7F21
TAG_CERTIFICATE_HOLDER_REFERENCE = 0x5F20
TAG_CERTIFICATE_VALID_UNTIL = 0x5F24
TAG_CERTIFICATE_VALID_FROM = 0x5F25
TAG_CERTIFICATE_SIGNATURE = 0x5F37
TAG_CERTIFICATE_SIGNATURE_REMAINDER = 0x5F38
TAG_CERTIFICATE_CONTENT = 0x5F4E
TAG_CERTIFICATE_CONTENT_CONSTRUCTED = 0x7F4E
TAG_CERTIFICATE_PUBLIC_KEY = 0x7F49
TAG_COPY_PROTECTION_CONTAINER = 0x7F70
TAG_PUBLIC_BYTES = 0x86
TAG_MOTICS_IDENTIFIER = 0x5F71
TAG_MOTICS_VERSION = 0x5F72
TAG_MOTICS_SE_ID = 0x5F73
TAG_MOTICS_RANDOM_DATA = 0x5F74
TAG_MOTICS_TIMESTAMP = 0x5F75
TAG_MOTICS_TIME_OFFSET = 0x5F76
TAG_MOTICS_APPLICATION_DATA = 0x5F77
TAG_MOTICS_SE_SIGNATURE = 0x5F78

VDV_TZ = pytz.timezone("Europe/Berlin")


class VDVException(Exception):
    pass


@dataclasses.dataclass
class Date:
    year: int
    month: int
    day: int

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def as_date(self):
        return datetime.date(self.year, self.month, self.day)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Date":
        if len(data) == 4:
            return cls(
                year=un_bcd(data[0:2]),
                month=un_bcd(data[2:3]),
                day=un_bcd(data[3:4])
            )
        elif len(data) == 3:
            return cls(
                year=2000 + un_bcd(data[0:1]),
                month=un_bcd(data[1:2]),
                day=un_bcd(data[2:3])
            )
        elif len(data) == 2:
            return cls(
                year=2000 + un_bcd(data[0:1]),
                month=un_bcd(data[1:2]),
                day=1
            )
        else:
            raise ValueError("Invalid date length")


@dataclasses.dataclass
class DateTime:
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}:{self.second:02d}"

    def as_datetime(self):
        dt = datetime.datetime(self.year, self.month, self.day, self.hour % 24, self.minute, self.second)
        dt += datetime.timedelta(days=self.hour // 24)
        return VDV_TZ.localize(dt)

    @classmethod
    def from_bytes(cls, data: bytes) -> "DateTime":
        if len(data) != 4:
            raise ValueError("Invalid date time length")

        year = data[0] >> 1
        month = ((data[0] & 0x01) << 3) | ((data[1] & 0xE0) >> 5)
        day = data[1] & 0x1F

        hour = (data[2] & 0xF8) >> 3
        minute = ((data[2] & 0x07) << 3) | ((data[3] & 0xE0) >> 5)
        second = (data[3] & 0x1F) * 2

        return cls(
            year=year + 1990,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second
        )

    def to_bytes(self) -> bytes:
        return bytes([
            ((self.year - 1990) << 1) | ((self.month >> 3) & 0x01),
            ((self.month << 5) & 0xE0) | self.day & 0x1F,
            ((self.hour & 0xF8) << 3) | ((self.minute >> 3) & 0x07),
            ((self.minute << 5) & 0xE0) | (self.second // 2) & 0x1F
        ])

def un_bcd(data: bytes) -> int:
    v = 0
    for i in range(len(data)):
        v *= 100
        v += ((data[i] & 0xF0) >> 4) * 10 + (data[i] & 0x0F)
    return v


def read_oid_component(int_bytes):
    ret = 0
    i = 0
    while int_bytes[i] & 0x80:
        num = int_bytes[i] & 0x7f
        if not ret and not num:
            raise VDVException("Leading 0x80 octets in the encoding of an OID component")
        ret |= num
        ret <<= 7
        i += 1

    ret |= int_bytes[i]
    return ret, i + 1


def decode_oid(data: bytes):
    components = []
    oid_offset = 0

    first, num = read_oid_component(data[oid_offset:])
    oid_offset += num
    if first < 40:
        components += [0, first]
    elif first < 80:
        components += [1, first - 40]
    else:
        components += [2, first - 80]

    while data[oid_offset:]:
        component, num = read_oid_component(data[oid_offset:])
        oid_offset += num
        components.append(component)

    return components
