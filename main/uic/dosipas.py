import typing
import pathlib
import asn1tools
import dataclasses


ROOT = pathlib.Path(__file__).parent
ASN1_SPEC_V1 = asn1tools.compile_files([ROOT / "asn1" / "uicBarcodeHeader_v1.0.0.asn"], codec="uper")
ASN1_SPEC_V2 = asn1tools.compile_files([ROOT / "asn1" / "uicBarcodeHeader_v2.0.1.asn"], codec="uper")


@dataclasses.dataclass
class DOSIPASEnvelope:
    version: int
    level_2_data: typing.Dict
    level_2_signature: bytes
    level_2_record: typing.Optional["Record"] = None
    records: typing.List["Record"] = dataclasses.field(default_factory=list)

    @classmethod
    def decode(cls, envelope: bytes) -> typing.Optional["DOSIPASEnvelope"]:
        out = None
        try:
            data = ASN1_SPEC_V2.decode("UicBarcodeHeader", envelope)
            if data["format"] == "U2":
                out = cls(
                    version=2,
                    level_2_data=data["level2SignedData"],
                    level_2_signature=data["level2Signature"],
                )
        except asn1tools.DecodeError:
            pass

        try:
            data = ASN1_SPEC_V1.decode("UicBarcodeHeader", envelope)
            if data["format"] == "U1":
                out = cls(
                    version=1,
                    level_2_data=data["level2SignedData"],
                    level_2_signature=data["level2Signature"],
                )
        except asn1tools.DecodeError:
            pass

        if out:
            if d := out.level_2_data.get("level2Data"):
                out.level_2_record = Record(
                    format=d["dataFormat"],
                    data=d["data"],
                )

            for r in out.level_2_data["level1Data"]["dataSequence"]:
                out.records.append(Record(
                    format=r["dataFormat"],
                    data=r["data"],
                ))

            return out

        return None


@dataclasses.dataclass
class Record:
    format: str
    data: bytes
