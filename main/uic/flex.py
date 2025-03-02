import typing
import dataclasses
import pathlib
import datetime
import asn1tools
import pytz
from . import util, fr_intercode

ROOT = pathlib.Path(__file__).parent
ASN1_SPEC_V1_3 = asn1tools.compile_files([ROOT / "asn1" / "uicRailTicketData_v1.3.4.asn"], codec="uper")
ASN1_SPEC_V2 = asn1tools.compile_files([ROOT / "asn1" / "uicRailTicketData_v2.0.2.asn"], codec="uper")
ASN1_SPEC_V3 = asn1tools.compile_files([ROOT / "asn1" / "uicRailTicketData_v3.0.3.asn"], codec="uper")

@dataclasses.dataclass
class Flex:
    version: int
    data: typing.Dict[str, typing.Any]
    intercode: typing.Optional[fr_intercode.FRIntercode] = None

    @classmethod
    def parse(cls, version: int, data: bytes) -> "Flex":
        try:
            if version in (1, 13):
                out = cls(
                    version=version,
                    data=ASN1_SPEC_V1_3.decode("UicRailTicketData", data)
                )
            elif version == 2:
                out = cls(
                    version=version,
                    data=ASN1_SPEC_V2.decode("UicRailTicketData", data)
                )
            elif version == 3:
                out = cls(
                    version=version,
                    data=ASN1_SPEC_V3.decode("UicRailTicketData", data)
                )
            else:
                raise util.UICException("Unsupported UIC rail ticket flexible data version")
        except asn1tools.DecodeError as e:
            raise util.UICException("Failed to decode UIC rail ticket flexible data") from e

        if out.data["issuingDetail"].get("extension"):
            extensionId = out.data["issuingDetail"]["extension"]["extensionId"]
            intercode_headers = [ "+FRII", "_1187II" ]
            for header in intercode_headers:
                if extensionId.startswith(header):
                    version = int(extensionId[len(header):])
                    out.intercode = fr_intercode.FRIntercode.parse(version, out.data["issuingDetail"]["extension"]["extensionData"])
                    break

        return out

    def issuing_rics(self) -> int:
        rics = self.data["issuingDetail"].get("issuerNum", 0)
        if rics:
            return rics
        else:
            return self.data["issuingDetail"].get("securityProviderNum", 0)

    def ticket_id(self) -> str:
        return self.data["issuingDetail"].get("issuerPNR", "")

    def issuing_time(self) -> typing.Optional[datetime.datetime]:
        date = datetime.datetime(self.data["issuingDetail"]["issuingYear"], 1, 1)
        date += datetime.timedelta(days=self.data["issuingDetail"]["issuingDay"] - 1)
        if "issuingTime" in self.data["issuingDetail"]:
            date += datetime.timedelta(minutes=self.data["issuingDetail"]["issuingTime"])
        return pytz.utc.localize(date)

    def specimen(self) -> bool:
        return self.data["issuingDetail"]["specimen"]