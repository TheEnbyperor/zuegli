import dataclasses
import typing

import ber_tlv.tlv
from .. import vdv
from .util import VDVNMException

@dataclasses.dataclass
class Authorization:

    @classmethod
    def parse(cls, data: bytes) -> "Authorization":
        try:
            data = ber_tlv.tlv.Tlv.parse(data)
        except Exception as e:
            raise VDVNMException("Failed to parse authorization") from e

        authorization = next(filter(lambda t: t[0] == 0xEA, data), None)
        if not authorization:
            raise VDVNMException("Not an authorization")
        authorization = authorization[1]


        return cls(
        )

# @dataclasses.dataclass
# class EFSAuthorization:
#     payment_type: int
#     traveler_type: int
#     name: str
#     gender: typing.Optional[vdv.ticket.Gender]
#     date_of_birth: typing.Optional[vdv.util.Date]
#     first_additional_travelers: typing.Optional[vdv.ticket.Mitnahme]
#     second_additional_travelers: typing.Optional[vdv.ticket.Mitnahme]
#
#     @classmethod
#     def parse(cls, data: bytes) -> "EFSAuthorization":
#         # if len(data) != 87:
#         #     raise VDVNMException("Not an EFS authorization")
#
#         return cls(
#             payment_type=data[0],
#             traveler_type=data[1],
#             name=data[2:42].decode("iso-8859-15", "replace"),
#             gender=vdv.ticket.Gender(data[42]) if data[42] != 0 else None,
#             date_of_birth=vdv.util.Date.from_bytes(data[43:47]) if all(d != 0 for d in data[43:47]) else None,
#             first_additional_travelers=vdv.ticket.Mitnahme(data[47], data[48]) if data[47] else None,
#             second_additional_travelers=vdv.ticket.Mitnahme(data[49], data[50]) if data[49] else None,
#         )
