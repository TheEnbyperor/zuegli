import typing
import dataclasses
import pathlib
import asn1tools
import base64
import datetime
import pytz
from . import util

ROOT = pathlib.Path(__file__).parent
ASN1_SPEC = asn1tools.compile_files([ROOT / "asn1" / "uicPretix.asn"], codec="uper")
WALLET_SPEC = asn1tools.compile_files([ROOT / "asn1" / "pretixWallet.asn"], codec="uper")
TOTP_SPEC = asn1tools.compile_files([ROOT / "asn1" / "pretixTotp.asn"], codec="uper")

@dataclasses.dataclass
class Pretix:
    data: typing.Dict[str, typing.Any]

    @classmethod
    def parse(cls, data: bytes) -> "Pretix":
        try:
            return cls(
                data=ASN1_SPEC.decode("PretixTicket", data)
            )
        except asn1tools.DecodeError as e:
            raise util.UICException("Failed to decode UIC Pretix data") from e

    def issuing_rics(self) -> int:
        rics = self.data["issuingDetail"].get("issuerNum", 0)
        sp_rics = self.data["issuingDetail"].get("securityProviderNum", 0)
        if sp_rics == 3634:
            return sp_rics
        if rics:
            return rics
        else:
            return sp_rics

    def ticket_id(self) -> str:
        return self.data["uniqueId"]

    def order_time(self) -> datetime.datetime:
        date = datetime.datetime(self.data["orderYear"], 1, 1)
        date += datetime.timedelta(days=self.data["orderDay"] - 1, minutes=self.data["orderTime"])
        return pytz.utc.localize(date)


@dataclasses.dataclass
class PretixWallet:
    data: typing.Dict[str, typing.Any]

    @classmethod
    def parse(cls, data: bytes) -> "PretixWallet":
        try:
            return cls(
                data=WALLET_SPEC.decode("PretixWallet", data)
            )
        except asn1tools.DecodeError as e:
            raise util.UICException("Failed to decode UIC Pretix wallet data") from e


@dataclasses.dataclass
class PretixTOTP:
    data: typing.Dict[str, typing.Any]

    @classmethod
    def parse(cls, data: bytes) -> "PretixTOTP":
        try:
            return cls(
                data=TOTP_SPEC.decode("PretixTotp", data)
            )
        except asn1tools.DecodeError as e:
            raise util.UICException("Failed to decode UIC Pretix TOTP data") from e