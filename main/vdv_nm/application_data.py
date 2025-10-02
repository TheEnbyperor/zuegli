import dataclasses
import ber_tlv.tlv
from .util import VDVNMException
from . import log


@dataclasses.dataclass
class ApplicationData:
    pv_key_version: int
    kvp_key_version: int
    auth_key_version: int
    issuing_transaction_sam_sequence_number: int
    issuing_transaction_sam_id: int
    issuance: log.ApplicationIssue

    @classmethod
    def parse(cls, data: bytes) -> "ApplicationData":
        try:
            data = ber_tlv.tlv.Tlv.parse(data)
        except Exception as e:
            raise VDVNMException("Failed to parse application data") from e

        data = next(filter(lambda t: t[0] == 0xEE, data), None)
        if not data:
            raise VDVNMException("Not application data")
        data = data[1]

        key_version = next(filter(lambda t: t[0] == 0x91, data), None)
        if not key_version:
            raise VDVNMException("Missing key version")
        key_version = key_version[1]
        if len(key_version) != 3:
            raise VDVNMException("Invalid key version")

        issuing_transaction = next(filter(lambda t: t[0] == 0x99, data), None)
        if not issuing_transaction:
            raise VDVNMException("Missing issuing transaction")
        issuing_transaction = issuing_transaction[1]

        if len(issuing_transaction) != 7:
            raise VDVNMException("Invalid issuing transaction")

        issuing_application = next(filter(lambda t: t[0] == 0xf7, data), None)
        if not issuing_application:
            raise VDVNMException("Missing issuing application")
        issuing_application = issuing_application[1]

        issuing_general_data = next(filter(lambda t: t[0] == 0x89, issuing_application), None)
        if not issuing_general_data:
            raise VDVNMException("Missing issuance general transaction data")
        issuing_general = log.GeneralData.parse(issuing_general_data[1])

        issuance = log.ApplicationIssue.parse(issuing_general, issuing_application)

        return cls(
            pv_key_version=key_version[0],
            kvp_key_version=key_version[1],
            auth_key_version=key_version[2],
            issuing_transaction_sam_sequence_number=int.from_bytes(issuing_transaction[0:4], "big"),
            issuing_transaction_sam_id=int.from_bytes(issuing_transaction[4:7], "big"),
            issuance=issuance,
        )
