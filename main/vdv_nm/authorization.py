import dataclasses
import ber_tlv.tlv
from . import log
from .util import VDVNMException


@dataclasses.dataclass
class Authorization:
    product_specific_data: bytes
    ticket_use: log.TicketUse
    pv_key_version: int
    kvp_key_version: int
    auth_key_version: int
    issuing_sam_sequence_number: int
    issuing_sam_id: int

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

        transaction = next(filter(lambda t: t[0] == 0xf1, authorization), None)
        if not transaction:
            raise VDVNMException("Missing transaction data")
        transaction = transaction[1]

        issuing_general_data = next(filter(lambda t: t[0] == 0x89, transaction), None)
        if not issuing_general_data:
            raise VDVNMException("Missing issuance general transaction data")
        issuing_general = log.GeneralData.parse(issuing_general_data[1])

        ticket_use = log.TicketUse.parse(issuing_general, transaction)

        product_specific_data = next(filter(lambda t: t[0] == 0x85, authorization), None)
        if not product_specific_data:
            raise VDVNMException("Missing product specific data")
        product_specific_data = product_specific_data[1]

        key_version = next(filter(lambda t: t[0] == 0x92, authorization), None)
        if not key_version:
            raise VDVNMException("Missing key version")
        key_version = key_version[1]
        if len(key_version) != 3:
            raise VDVNMException("Invalid key version")

        issuing_sam_data = next(filter(lambda t: t[0] == 0x99, authorization), None)
        if not issuing_sam_data:
            raise VDVNMException("Missing issuing SAM data")
        issuing_sam_data = issuing_sam_data[1]
        if len(issuing_sam_data) != 7:
            raise VDVNMException("Invalid issuing SAM data")

        return cls(
            product_specific_data=product_specific_data,
            ticket_use=ticket_use,
            pv_key_version=key_version[0],
            kvp_key_version=key_version[1],
            auth_key_version=key_version[2],
            issuing_sam_sequence_number=int.from_bytes(issuing_sam_data[0:4], "big"),
            issuing_sam_id=int.from_bytes(issuing_sam_data[4:7], "big"),
        )
