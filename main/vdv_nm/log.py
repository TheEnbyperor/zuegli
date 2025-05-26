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

    if log_type == 0xf1:
        return TicketUse.parse(general, data)
    elif log_type == 0xf3:
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
    def type(self):
        raise NotImplementedError()

    def type_name(self):
        raise NotImplementedError()


@dataclasses.dataclass
class TicketUse(LogEntry):
    general: GeneralData

    def type_name(self):
        return "Ticket use"

    @classmethod
    def parse(cls, general: GeneralData, data):
        return cls(
            general=general,
        )


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
    application_sam_sequence_number: int
    application_log_sequence_number: int
    application_instance_number: int
    application_instance_org_id: int
    old_status: int
    new_status: int
    application_synchronisation_number: int
    control_mac: bytes
    control_key_version: int

    def type(self):
        return "application-issue"

    def type_name(self):
        return "Application issue"

    def application_instance_org_name(self):
        return vdv.ticket.map_org_id(self.application_instance_org_id)

    def application_instance_org_name_opt(self):
        return vdv.ticket.map_org_id(self.application_instance_org_id, True)

    @classmethod
    def parse(cls, general: GeneralData, data):
        app_sam_seq = next(filter(lambda t: t[0] == 0x9b, data), None)
        if not app_sam_seq:
            raise VDVNMException("Missing application SAM sequence number")
        app_sam_seq = app_sam_seq[1]
        if len(app_sam_seq) != 4:
            raise VDVNMException("Invalid application SAM sequence number")

        status_change = next(filter(lambda t: t[0] == 0x8e, data), None)
        if not status_change:
            raise VDVNMException("Missing status change")
        status_change = status_change[1]
        if len(status_change) != 20:
            raise VDVNMException("Invalid status change")

        return cls(
            general=general,
            application_sam_sequence_number=int.from_bytes(app_sam_seq, "big"),
            application_log_sequence_number=int.from_bytes(status_change[0:2], "big"),
            application_instance_number=int.from_bytes(status_change[2:6], "big"),
            application_instance_org_id=int.from_bytes(status_change[6:8], "big"),
            old_status=status_change[8],
            new_status=status_change[9],
            application_synchronisation_number=status_change[10],
            control_mac=status_change[11:19],
            control_key_version=status_change[19],
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