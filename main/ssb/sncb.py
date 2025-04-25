import dataclasses
import re
import typing
import pathlib
import json
from .. import vdv

SNCB_RE = re.compile(r"^(?P<product_code>[\w\d]{3,})( (?P<forename>[\w\d]{1,2}) (?P<surname>[\w\d]{1,2}))?$")

SNCB_PRODUCTS = None
ROOT_DIR = pathlib.Path(__file__).parent.parent


def get_sncb_producs():
    global SNCB_PRODUCTS

    if SNCB_PRODUCTS:
        return SNCB_PRODUCTS

    with open(ROOT_DIR / "uic" / "data" / "sncb_products.json") as f:
        SNCB_PRODUCTS = json.load(f)

    return SNCB_PRODUCTS

@dataclasses.dataclass
class SNCBData:
    product_code: str
    product_name: typing.Optional[str] = None
    forename: typing.Optional[str] = None
    original_forename: typing.Optional[str] = None
    surname: typing.Optional[str] = None
    original_surname: typing.Optional[str] = None

    @classmethod
    def parse(cls, data: str, context: vdv.ticket.Context) -> typing.Optional["SNCBData"]:
        if match := SNCB_RE.match(data):
            out = cls(
                product_code=match.group("product_code"),
                forename=match.group("forename"),
                surname=match.group("surname")
            )

            if out.forename and context.account_forename and context.account_forename.upper().startswith(out.forename):
                out.original_forename = out.forename
                out.forename = context.account_forename
            if out.surname and context.account_surname and context.account_surname.upper().startswith(out.surname):
                out.original_surname = out.surname
                out.surname = context.account_surname

            if product_name := get_sncb_producs().get(out.product_code):
                out.product_name = product_name

            return out

        return None
