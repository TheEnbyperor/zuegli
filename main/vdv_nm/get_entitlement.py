import dataclasses
import ber_tlv.tlv
from .util import VDVNMException

@dataclasses.dataclass
class GetEntitlement:
    sam_challenge: bytes
    nm_challenge: bytes
    data: bytes
    mac: bytes

    @classmethod
    def parse(cls, data: bytes, sam_challenge: bytes) -> "GetEntitlement":
        try:
            data = ber_tlv.tlv.Tlv.parse(data)
        except Exception as e:
            raise VDVNMException("Failed to parse get entitlement response") from e

        nm_challenge = next(filter(lambda t: t[0] == 0x80, data), None)
        if not nm_challenge:
            raise VDVNMException("No NM challenge")
        nm_challenge = nm_challenge[1]

        protected_data = next(filter(lambda t: t[0] == 0x81, data), None)
        if not protected_data:
            raise VDVNMException("No protected data")
        protected_data = protected_data[1]

        mac = next(filter(lambda t: t[0] == 0x8E, data), None)
        if not mac:
            raise VDVNMException("No MAC")
        mac = mac[1]

        return cls(
            sam_challenge=sam_challenge,
            nm_challenge=nm_challenge,
            data=protected_data,
            mac=mac
        )

