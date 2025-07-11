import dataclasses
import datetime
import typing

BASE30_ALPHABET= "BCDEFGHJKLMNPQRSTVWXYZ23456789"

def decode_base30(base30: str) -> int:
    num = 0
    for char in base30:
        num *= len(BASE30_ALPHABET)
        i = BASE30_ALPHABET.index(char)
        num += i
    return num


@dataclasses.dataclass
class UTN:
    transaction_number: int
    machine_number: int
    day_of_issue: int

    @classmethod
    def from_int(cls, num: int) -> "UTN":
        return cls(
            transaction_number=num & 0x1FFFF,
            machine_number=(num >> 17) & 0x3FFF,
            day_of_issue=(num >> 31) & 0x7FF
        )

    def date_of_issue(self, issuer_id: typing.Optional[str] = None) -> datetime.date:
        today = datetime.date.today()
        epoch = datetime.date(year=2015, month=12, day=31)
        date_of_issue_tmp = epoch + datetime.timedelta(days=self.day_of_issue)
        date_of_issue = date_of_issue_tmp
        while date_of_issue_tmp < today:
            date_of_issue = date_of_issue_tmp
            epoch = datetime.date(year=epoch.year + 5, month=12, day=31)
            date_of_issue_tmp = epoch + datetime.timedelta(days=self.day_of_issue)

        if issuer_id in ("TP", "TV", "TK", "TS"):
            date_of_issue_ttk_tmp = datetime.date(year=2015, month=12, day=31) + datetime.timedelta(days=self.day_of_issue)
            date_of_issue_ttk = date_of_issue_ttk_tmp
            while date_of_issue_ttk_tmp < today:
                date_of_issue_ttk = date_of_issue_ttk_tmp
                date_of_issue_ttk_tmp += datetime.timedelta(days=2048)

            if date_of_issue_ttk > date_of_issue:
                return date_of_issue_ttk

        return date_of_issue