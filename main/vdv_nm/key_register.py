import dataclasses
import typing
import ber_tlv.tlv
from .util import VDVNMException
from .. import vdv

@dataclasses.dataclass
class Key:
    key_id: int
    key_version: int
    org_id: int

    @property
    def key_id_hex(self):
        return f"0x{self.key_id:2X}"

    def org_name(self):
        return vdv.ticket.map_org_id(self.org_id)

    def org_name_opt(self):
        return vdv.ticket.map_org_id(self.org_id, True)

    @classmethod
    def parse(cls, data: bytes):
        if len(data) != 4:
            raise VDVNMException("Invalid key data")

        return cls(
            key_id=data[0],
            key_version=data[1],
            org_id=int.from_bytes(data[2:4], byteorder="big"),
        )


@dataclasses.dataclass
class KeyRegister:
    keys: typing.List[Key]

    @classmethod
    def parse(cls, data: bytes) -> "KeyRegister":
        try:
            data = ber_tlv.tlv.Tlv.parse(data)
        except Exception as e:
            raise VDVNMException("Failed to parse key register") from e

        data = next(filter(lambda t: t[0] == 0xED, data), None)
        if not data:
            raise VDVNMException("Not a key register")
        data = data[1]

        if len(data) % 4 != 0:
            raise VDVNMException("Invalid key register")

        keys = [Key.parse(data[i:i+4]) for i in range(0, len(data), 4)]

        return cls(
            keys=keys,
        )
