import json
import typing
import dataclasses
import pathlib
import asn1tools
from . import util

ROOT = pathlib.Path(__file__).parent
INTERCODE_DATA = None
ASN1_SPEC_V1 = asn1tools.compile_files([ROOT / "asn1" / "sncf_transport_v1.asn"], codec="uper")

@dataclasses.dataclass
class SNCFTransport:
    version: int
    data: typing.Dict[str, typing.Any]

    @classmethod
    def parse(cls, version: int, data: bytes) -> "SNCFTransport":
        try:
            if version == 1:
                return cls(
                    version=version,
                    data=ASN1_SPEC_V1.decode("SncfTransportData", data)
                )
            else:
                raise util.UICException("Unsupported SNCF transport data version")
        except asn1tools.DecodeError as e:
            raise util.UICException("Failed to decode SNCF transport data") from e


def get_intercode_data():
    global INTERCODE_DATA

    if INTERCODE_DATA:
        return INTERCODE_DATA

    with open(ROOT / "data" / "sncf_ids.json") as f:
        INTERCODE_DATA = json.load(f)

    return INTERCODE_DATA