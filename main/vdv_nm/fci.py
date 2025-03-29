import dataclasses
import ber_tlv.tlv
from .. import vdv
from . import util
from .util import VDVNMException

@dataclasses.dataclass
class FCI:
    aid: bytes
    manufacturer_org_id: int
    spec_version: str
    manufacturer_version_number: bytes

    def manufacturer_org_name(self):
        return vdv.ticket.map_org_id(self.manufacturer_org_id)

    def manufacturer_org_name_opt(self):
        return vdv.ticket.map_org_id(self.manufacturer_org_id, True)

    @classmethod
    def parse(cls, data: bytes) -> "FCI":
        try:
            data = ber_tlv.tlv.Tlv.parse(data)
        except Exception as e:
            raise VDVNMException("Failed to parse FCI") from e

        fci = next(filter(lambda t: t[0] == 0x6F, data), None)
        if not fci:
            raise VDVNMException("Not an FCI")
        fci = fci[1]

        aid = next(filter(lambda t: t[0] == 0x84, fci), None)
        proprietary_information = next(filter(lambda t: t[0] == 0xA5, fci), None)

        if not aid:
            raise VDVNMException("Invalid FCI - no AID")
        aid = aid[1]

        if aid != util.VDV_KA_NM_AID:
            raise VDVNMException("Unable to parse FCI - not a VDV-KA application")

        if not proprietary_information:
            raise VDVNMException("Invalid FCI - no proprietary information")
        proprietary_information = proprietary_information[1]

        application_version = next(filter(lambda t: t[0] == 0x80, proprietary_information), None)
        if not application_version:
            raise VDVNMException("Invalid FCI - no application version data")
        application_version = application_version[1]

        if len(application_version) < 8:
            raise VDVNMException("Invalid FCI - application version data too short")

        return cls(
            aid=aid,
            manufacturer_org_id=int.from_bytes(application_version[0:2], "big"),
            spec_version=vdv.util.parse_version_number(application_version[2:4]),
            manufacturer_version_number=application_version[4:8],
        )
