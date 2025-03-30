import dataclasses
import ber_tlv.tlv
from . util import VDVNMException

@dataclasses.dataclass
class InfoText:
    text: str

    @classmethod
    def parse(cls, data: bytes) -> "InfoText":
        try:
            data = ber_tlv.tlv.Tlv.parse(data)
        except Exception as e:
            raise VDVNMException("Failed to parse info text") from e

        info_text = next(filter(lambda t: t[0] == 0xC7, data), None)
        if not info_text:
            raise VDVNMException("Not an info text")
        info_text = info_text[1].strip(b"\x00")

        return cls(
            text=info_text.decode("utf-8"),
        )
