from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional


@dataclass
class FareLocationsReferenceData:
    fare_location: List["FareLocationsReferenceData.FareLocation"] = field(
        default_factory=list,
        metadata={
            "name": "FareLocation",
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
    class FareLocation:
        nlc: Optional[str] = field(
            default=None,
            metadata={
                "name": "Nlc",
                "type": "Element",
                "namespace": "",
                "required": True,
                "max_length": 4,
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
        used_by_wct: Optional[bool] = field(
            default=None,
            metadata={
                "name": "UsedByWct",
                "type": "Element",
                "namespace": "",
                "required": True,
            },
        )
