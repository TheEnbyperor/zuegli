import dataclasses
import datetime
import pytz
import typing
import decimal
from . import util
from django.utils.translation import gettext_lazy as _


ISSUER_TIMEZONES = {
    "M0": pytz.timezone("America/New_York"),
    "MA": pytz.timezone("America/New_York"),
    "RP": pytz.timezone("America/Denver"),
}


def as_int(content: bytes, _) -> int:
    return int.from_bytes(content, byteorder="big", signed=False)


def as_bool(content: bytes, _) -> bool:
    if len(content) != 1:
        raise util.FTException("Boolean payload must be exactly 1 byte")
    return content[0] != 0


def as_string(content: bytes, _) -> str:
    return content.decode("utf-8")


def as_datetime(content: bytes, issuer_id: str) -> datetime.datetime:
    v = as_int(content, issuer_id) / 1000
    dt = datetime.datetime.fromtimestamp(v, pytz.utc)
    return dt.astimezone(ISSUER_TIMEZONES.get(issuer_id, pytz.utc))


def as_currency(content: bytes, issuer_id: str) -> decimal.Decimal:
    return decimal.Decimal(as_int(content, issuer_id)) / decimal.Decimal(100)

ELEMENT_KEYS = {
    1: ("SCHEMA_VERSION", as_int),
    2: ("E_TICKET_NUMBER", as_string),
    6: ("DISCOUNT_TYPE_ID", None),
    7: ("IDENTITY_INFORMATION", None),
    9: ("FROM_STATION_NUMBER", as_int),
    10: ("VIA_STATION_NUMBER", as_int),
    11: ("TO_STATION_NUMBER", as_int),
    12: ("PURCHASE_UTC_DATE_TIME", as_datetime),
    13: ("VALIDITY_START_UTC_DATE_TIME", as_datetime),
    14: ("VALIDITY_EXPIRY_UTC_DATE_TIME", as_datetime),
    15: ("USE_PERIOD_SPECIFICATION_BYTE_ARRAY", None),
    18: ("ACTIVATION_DURATION_MINS", as_int),
    21: ("NUM_RIDERS_SERVER_ENCODED", None),
    23: ("NUM_TICKETS_IN_PURCHASED_PRODUCT", as_int),
    24: ("USES_PERMITTED", as_int),
    25: ("PRICE", as_currency),
    26: ("CARDHOLDER_NAME", as_string),
    27: ("CARD_LAST_FOUR_DIGITS", as_string),
    28: ("EMAIL_ADDRESS", as_string),
    29: ("MODE_OF_TRANSPORT", None),
    30: ("PARENT_PRODUCT_ID_STRING", as_string),
    32: ("UNIQUE_USER_ID", as_string),
    33: ("PRODUCT_ID_STRING", as_string),
    34: ("CUSTOMER_PRODUCT_REFERENCE_STRING", as_string),
    35: ("MEDIA_CHANNEL", as_int),
    36: ("RESERVED_SEAT", None),
    37: ("SERVICE_ID", None),
    38: ("INTEROP_NUMBER", None),
    45: ("NUMBER_OF_RIDERS", as_int),
    46: ("ACTIVATION_START_UTC_DATE_TIME", as_datetime),
    47: ("DEVICE_DATE_TIME", as_datetime),
    48: ("GEO_LATITUDE", None),
    49: ("GEO_LONGITUDE", None),
    53: ("SELECTED_FOR_VALIDATION", as_bool),
    51: ("USES_COUNT", as_int),
    50: ("USES_REMAINING", as_int),
    52: ("USE_PERIOD_EXPIRY_UTC_DATE_TIME", as_datetime),
}


@dataclasses.dataclass
class Element:
    cid: int
    value: bytes

    @property
    def key(self):
        if self.cid in ELEMENT_KEYS:
            return ELEMENT_KEYS[self.cid][0]
        else:
            return "UNKNOWN"

    def decoded_value(self, issuer_id: str):
        if self.cid in ELEMENT_KEYS:
            if d := ELEMENT_KEYS[self.cid][1]:
                return d(self.value, issuer_id)
            return self.value
        else:
            return self.value

@dataclasses.dataclass
class Data:
    _items: typing.Dict[str, typing.Any]

    @staticmethod
    def decode_length_from_code(code: int) -> int:
        if code == 0:
            return 1
        elif code == 1:
            return 2
        elif code == 2:
            return 4
        else:
            raise util.FTException(f"Invalid small/medium length code: {code}")

    @classmethod
    def decode_element(cls, data: bytes):
        b0 = data[0]
        # Large header
        if b0 == 0xFF:
            if len(data) < 3:
                raise util.FTException("Truncated large header")
            cid = 63 + data[1]
            length = data[2]
            hsize = 3
        else:
            hi6 = b0 >> 2
            len_code = b0 & 0x03
            # Medium variant 2 header
            if hi6 == 63:
                if len(data) < 2:
                    raise util.FTException("Truncated medium variant 2 header")
                cid = 63 + data[1]
                length = cls.decode_length_from_code(len_code)
                hsize = 2
            # Medium variant 1 header
            elif len_code == 3:
                if len(data) < 2:
                    raise util.FTException("Truncated medium variant 1 header")
                cid = hi6
                length = data[1]
                hsize = 2
            # Small header
            else:
                cid = hi6
                length = cls.decode_length_from_code(len_code)
                hsize = 1

        size = hsize + length
        if len(data) < size:
            raise util.FTException("Truncated payload content")
        content = data[hsize:size]

        return cid, content, size

    @classmethod
    def decode_all(cls, data: bytes):
        elements = []
        while data:
            if data[0] == 0x00:
                break
            cid, content, size = cls.decode_element(data)
            data = data[size:]
            elements.append(Element(cid=cid, value=content))
        return elements

    @classmethod
    def parse(cls, data: bytes, issuer_id: str):
        data = cls.decode_all(data)
        items = {}
        for e in data:
            items[e.key] = e.decoded_value(issuer_id)
        return cls(items)

    def __getattr__(self, item):
        if item in self._items:
            return self._items[item]
        else:
            raise AttributeError(item)

    def activation_duration(self) -> typing.Optional[datetime.timedelta]:
        if "ACTIVATION_DURATION_MINS" in self._items:
            return datetime.timedelta(minutes=self._items["ACTIVATION_DURATION_MINS"])
        else:
            return None

    def price_str(self) -> str:
        return f"${self.PRICE:.2f}"

    def uses_permitted_str(self):
        if self.USES_PERMITTED == 255:
            return _("Unlimited")
        else:
            return str(self.USES_PERMITTED)