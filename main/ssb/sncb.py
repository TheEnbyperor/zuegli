import dataclasses
import re
import typing
from .. import vdv

SNCB_RE = re.compile(r"^(?P<product_code>[\w\d]{3,}) (?P<forename>[\w\d]{1,2}) (?P<surname>[\w\d]{1,2})$")

@dataclasses.dataclass
class SNCBData:
    product_code: str
    forename: str
    original_forename: typing.Optional[str]
    surname: str
    original_surname: typing.Optional[str]

    @classmethod
    def parse(cls, data: str, context: vdv.ticket.Context) -> typing.Optional["SNCBData"]:
        if match := SNCB_RE.match(data):
            forename = match.group("forename")
            surname = match.group("surname")
            original_forename = None
            original_surname = None

            if context.account_forename.upper().startswith(forename):
                original_forename = forename
                forename = context.account_forename
            if context.account_surname.upper().startswith(surname):
                original_surname = surname
                surname = context.account_surname

            return cls(
                product_code=match.group("product_code"),
                forename=forename,
                original_forename=original_forename,
                surname=surname,
                original_surname=original_surname,
            )
