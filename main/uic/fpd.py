import dataclasses
import pathlib
import asn1tools
import typing
from . import util

ROOT = pathlib.Path(__file__).parent
ASN1_SPEC_TCS = asn1tools.compile_files([
    ROOT / "asn1" / "uicFixedPointData_v1.0.0_draft_tcs.asn",
    ROOT / "asn1" / "uicRailTicketData_v4.0.0_draft_tcs.asn",
], codec="uper")
ASN1_SPEC = asn1tools.compile_files([
    ROOT / "asn1" / "uicFixedPointData_v1.0.0_draft.asn",
    ROOT / "asn1" / "uicGeneralData_v1.0.0_draft.asn",
], codec="uper")

@dataclasses.dataclass
class FixedPointData:
    data: typing.Dict[str, typing.Any]

    @classmethod
    def parse_tcs(cls, data: bytes) -> "FixedPointData":
        try:
            return cls(
                data=ASN1_SPEC_TCS.decode("FixedPointData", data)
            )
        except asn1tools.DecodeError as e:
            raise util.UICException("Failed to decode UIC Fixed Point Data (TCS draft)") from e

    @classmethod
    def parse(cls, data: bytes) -> "FixedPointData":
        try:
            return cls(
                data=ASN1_SPEC.decode("FixedPointData", data)
            )
        except asn1tools.DecodeError as e:
            raise util.UICException("Failed to decode UIC Fixed Point Data") from e

    def id(self) -> str:
        if self.data["id"][0] == "idNum":
            return str(self.data["id"][1])
        elif self.data["id"][0] == "idIA5":
            return self.data["id"][1]
        elif self.data["id"][0] == "idOct":
            return ":".join(f"{b:02x}" for b in self.data["id"][1])
        else:
            return ""