import abc
import ber_tlv.tlv
import dataclasses
from .. import vdv
from .util import VDVNMException

def parse_log(data: bytes):
    try:
        data = ber_tlv.tlv.Tlv.parse(data)
    except Exception as e:
        raise VDVNMException("Failed to parse log entry") from e

    if len(data) != 1:
        raise VDVNMException("Failed to parse log entry")

    log_type = data[0][0]
    data = data[0][1]

    general_data = next(filter(lambda t: t[0] == 0x89, data), None)
    if not general_data:
        raise VDVNMException("Missing general transaction data")
    general_data = general_data[1]

    general = GeneralData.parse(general_data)

    if log_type == 0xf3:
        return AuthorizationBlock.parse(general, data)
    elif log_type == 0xf4:
        return ApplicationBlock.parse(general, data)
    elif log_type == 0xf6:
        return AuthorizationIssue.parse(general, data)
    elif log_type == 0xf7:
        return ApplicationIssue.parse(general, data)
    elif log_type == 0xf9:
        return AuthorizationCancel.parse(general, data)
    elif log_type == 0xfa:
        return ApplicationCancel.parse(general, data)
    elif log_type == 0x8d:
        return AuthorizationUpdate.parse(general, data)
    elif log_type == 0x8e:
        return ApplicationUpdate.parse(general, data)
    else:
        raise VDVNMException(f"Unknown log type {log_type:02x}")


@dataclasses.dataclass
class GeneralData:
    sequence_number: int
    sam_sequence_number: int
    sam_id: int
    operator_org_id: int
    terminal_type: int
    terminal_number: int
    terminal_org_id: int
    timestamp: vdv.util.DateTime
    location_type: int
    location_number: int
    location_org_id: int
    transaction_type: int

    def operator_org_name(self):
        return vdv.ticket.map_org_id(self.operator_org_id)

    def operator_org_name_opt(self):
        return vdv.ticket.map_org_id(self.operator_org_id, True)

    def terminal_type_name(self, opt=False):
        return vdv.ticket.terminal_type_name(self.terminal_type, opt)

    def terminal_type_name_opt(self):
        return vdv.ticket.terminal_type_name(self.terminal_type, True)

    def terminal_org_name(self):
        return vdv.ticket.map_org_id(self.terminal_org_id)

    def terminal_org_name_opt(self):
        return vdv.ticket.map_org_id(self.terminal_org_id, True)

    def location_type_name(self, opt=False):
        return vdv.ticket.location_name(self.location_type, opt)

    def location_type_name_opt(self):
        return vdv.ticket.location_name(self.location_type, True)

    def location_org_name(self):
        return vdv.ticket.map_org_id(self.location_org_id)

    def location_org_name_opt(self):
        return vdv.ticket.map_org_id(self.location_org_id, True)

    @classmethod
    def parse(cls, data: bytes):
        if len(data) != 27:
            raise VDVNMException("Invalid general transaction data")

        return cls(
            sequence_number=int.from_bytes(data[0:2], "big"),
            sam_sequence_number=int.from_bytes(data[2:6], "big"),
            sam_id=int.from_bytes(data[6:9], "big"),
            operator_org_id=int.from_bytes(data[9:11], "big"),
            terminal_type=data[11],
            terminal_number=int.from_bytes(data[12:14], "big"),
            terminal_org_id=int.from_bytes(data[14:16], "big"),
            timestamp=vdv.util.DateTime.from_bytes(data[16:20]),
            location_type=data[20],
            location_number=int.from_bytes(data[21:24], "big"),
            location_org_id=int.from_bytes(data[24:26], "big"),
            transaction_type=data[26],
        )


class LogEntry(abc.ABC):
    def type_name(self):
        raise NotImplementedError()


@dataclasses.dataclass
class AuthorizationBlock(LogEntry):
    general: GeneralData

    def type_name(self):
        return "Authorization block"

    @classmethod
    def parse(cls, general: GeneralData, data):
        return cls(
            general=general,
        )


@dataclasses.dataclass
class AuthorizationIssue(LogEntry):
    general: GeneralData

    def type_name(self):
        return "Authorization issue"

    @classmethod
    def parse(cls, general: GeneralData, data):
        return cls(
            general=general,
        )

@dataclasses.dataclass
class AuthorizationCancel(LogEntry):
    general: GeneralData

    def type_name(self):
        return "Authorization cancel"

    @classmethod
    def parse(cls, general: GeneralData, data):
        return cls(
            general=general,
        )


@dataclasses.dataclass
class AuthorizationUpdate(LogEntry):
    general: GeneralData

    def type_name(self):
        return "Authorization update"

    @classmethod
    def parse(cls, general: GeneralData, data):
        return cls(
            general=general,
        )


@dataclasses.dataclass
class ApplicationBlock(LogEntry):
    general: GeneralData

    def type_name(self):
        return "Application block"

    @classmethod
    def parse(cls, general: GeneralData, data):
        return cls(
            general=general,
        )


@dataclasses.dataclass
class ApplicationIssue(LogEntry):
    general: GeneralData

    def type_name(self):
        return "Application issue"

    @classmethod
    def parse(cls, general: GeneralData, data):
        return cls(
            general=general,
        )


@dataclasses.dataclass
class ApplicationCancel(LogEntry):
    general: GeneralData

    def type_name(self):
        return "Application cancel"

    @classmethod
    def parse(cls, general: GeneralData, data):
        return cls(
            general=general,
        )


@dataclasses.dataclass
class ApplicationUpdate(LogEntry):
    general: GeneralData

    def type_name(self):
        return "Application update"

    @classmethod
    def parse(cls, general: GeneralData, data):
        return cls(
            general=general,
        )