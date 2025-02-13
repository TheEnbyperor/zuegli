import typing
import datetime
import dataclasses
import pytz
from .. import vdv

class BravoException(Exception):
    pass


@dataclasses.dataclass
class BravoRecord:
    valid_from: typing.Optional[datetime.datetime] = None
    valid_to: typing.Optional[datetime.datetime] = None
    ticket_pnr: typing.Optional[str] = None
    ticket_number: typing.Optional[int] = None
    product_id: typing.Optional[int] = None
    product_rics: typing.Optional[int] = None

    @classmethod
    def parse(cls, data: bytes):
        tags = {}
        offset = 0
        while offset < len(data):
            if offset + 2 > len(data):
                raise BravoException("Invalid TLV, not enough data")

            tag = data[offset]
            length = data[offset + 1]

            if offset + 2 + length > len(data):
                raise BravoException("Invalid TLV, not enough data")

            d = data[offset + 2:offset + 2 + length]
            offset += 2 + length

            tags[tag] = d

        out = cls()

        if validity := tags.pop(3, None):
            if len(validity) != 8:
                raise BravoException("Invalid validity record, wrong length")

            tz = pytz.timezone("Europe/Amsterdam")
            out.valid_from = vdv.util.DateTime.from_bytes(validity[0:4]).as_datetime(tz)
            out.valid_to = vdv.util.DateTime.from_bytes(validity[4:8]).as_datetime(tz)

        if ticket_id := tags.pop(2, None):
            out.ticket_pnr = ticket_id[0:15].decode("ascii")
            out.ticket_number = int.from_bytes(ticket_id[15:19], "big")

        if product := tags.pop(1, None):
            out.product_id = int.from_bytes(product[0:2], "big")
            out.product_rics = int.from_bytes(product[2:4], "big")

        return out
