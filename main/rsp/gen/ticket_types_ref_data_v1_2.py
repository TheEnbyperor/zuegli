from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class TicketTypesReferenceData:
    ticket_type: list["TicketTypesReferenceData.TicketType"] = field(
        default_factory=list,
        metadata={
            "name": "TicketType",
            "type": "Element",
            "namespace": "",
        },
    )
    version: Optional[Decimal] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "required": True,
        },
    )

    @dataclass
    class TicketType:
        code: Optional[str] = field(
            default=None,
            metadata={
                "name": "Code",
                "type": "Element",
                "namespace": "",
                "required": True,
                "max_length": 3,
            },
        )
        name: Optional[str] = field(
            default=None,
            metadata={
                "name": "Name",
                "type": "Element",
                "namespace": "",
                "required": True,
            },
        )
        ojpenabled: Optional[bool] = field(
            default=None,
            metadata={
                "name": "OJPEnabled",
                "type": "Element",
                "namespace": "",
                "required": True,
            },
        )
        ojpdisplay_name: Optional[str] = field(
            default=None,
            metadata={
                "name": "OJPDisplayName",
                "type": "Element",
                "namespace": "",
                "required": True,
            },
        )
        ojpadvice_message: Optional[str] = field(
            default=None,
            metadata={
                "name": "OJPAdviceMessage",
                "type": "Element",
                "namespace": "",
                "required": True,
            },
        )
        rspdisplay_name: Optional[str] = field(
            default=None,
            metadata={
                "name": "RSPDisplayName",
                "type": "Element",
                "namespace": "",
                "required": True,
                "max_length": 255,
            },
        )
        rspadvice: Optional[str] = field(
            default=None,
            metadata={
                "name": "RSPAdvice",
                "type": "Element",
                "namespace": "",
                "required": True,
                "max_length": 255,
            },
        )
        attended_tis: Optional[bool] = field(
            default=None,
            metadata={
                "name": "AttendedTIS",
                "type": "Element",
                "namespace": "",
                "required": True,
            },
        )
        unattended_tis: Optional[bool] = field(
            default=None,
            metadata={
                "name": "UnattendedTIS",
                "type": "Element",
                "namespace": "",
                "required": True,
            },
        )
