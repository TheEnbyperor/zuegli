import re
import datetime
import typing
import dataclasses
from .util import BahnBonusException
from . import products

BB_RE = re.compile(r"^(?P<product_id>[\w\d]{12});(?P<barcode_id>[\w\d-]+)(?:;(?P<valid_from>[\d-]+);(?P<valid_until>[\d-]+);(?P<issuer>[\w\d]+))?$")

def is_bahnbonus_code(code: bytes) -> bool:
    try:
        code = code.decode("utf-8")
    except UnicodeDecodeError:
        return False

    return BB_RE.fullmatch(code) is not None


@dataclasses.dataclass
class BahnBonusCode:
    product_id: str
    barcode_id: str
    valid_from: typing.Optional[datetime.date]
    valid_until: typing.Optional[datetime.date]
    issuer: typing.Optional[str]

    @classmethod
    def parse(cls, code: bytes) -> "BahnBonusCode":
        try:
            code = code.decode("utf-8")
        except UnicodeDecodeError as e:
            raise BahnBonusException("Invalid BahnBonus code") from e

        m = BB_RE.fullmatch(code)
        if m is None:
            raise BahnBonusException("Not a BahnBonus code")

        out = cls(
            product_id=m.group("product_id"),
            barcode_id=m.group("barcode_id"),
            valid_from=None,
            valid_until=None,
            issuer=m.group("issuer"),
        )

        valid_from = m.group("valid_from")
        valid_until = m.group("valid_until")

        if valid_from is not None:
            out.valid_from = datetime.datetime.strptime(valid_from, "%Y-%m-%d").date()
        if valid_until is not None:
            out.valid_until = datetime.datetime.strptime(valid_until, "%Y-%m-%d").date()

        return out

    def product(self) -> typing.Optional[products.Product]:
        if self.product_id in products.PRODUCTS:
            return products.PRODUCTS[self.product_id]
        return None
