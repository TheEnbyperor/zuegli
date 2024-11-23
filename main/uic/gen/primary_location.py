from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

__NAMESPACE__ = "http://ws.refdata.crd.cc.uic.org/replication/schemas"


@dataclass
class ActiveFlag:
    class Meta:
        name = "Active_Flag"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: Optional[bool] = field(
        default=None,
        metadata={
            "required": True,
        },
    )


@dataclass
class AddDate:
    class Meta:
        name = "Add_Date"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "pattern": r"\d{4}[-](0[1-9]|1[012])[-](0[1-9]|[12][0-9]|3[01])",
        },
    )


@dataclass
class ContainerHandlingFlag:
    class Meta:
        name = "Container_Handling_Flag"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: Optional[bool] = field(
        default=None,
        metadata={
            "required": True,
        },
    )


@dataclass
class CountryIsoCode2:
    class Meta:
        name = "Country_Iso_Code"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "min_length": 2,
            "max_length": 2,
        },
    )


@dataclass
class EndValidity:
    class Meta:
        name = "End_Validity"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "pattern": r"\d{4}[-](0[1-9]|1[012])[-](0[1-9]|[12][0-9]|3[01])",
        },
    )


@dataclass
class FreeText:
    class Meta:
        name = "Free_Text"
        nillable = True
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: Optional[str] = field(
        default="",
        metadata={
            "min_length": 0,
            "max_length": 255,
            "nillable": True,
        },
    )


@dataclass
class FreightEndValidity:
    class Meta:
        name = "Freight_End_Validity"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "pattern": r"\d{4}[-](0[1-9]|1[012])[-](0[1-9]|[12][0-9]|3[01])",
        },
    )


@dataclass
class FreightPossibleFlag:
    class Meta:
        name = "Freight_Possible_Flag"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: Optional[bool] = field(
        default=None,
        metadata={
            "required": True,
        },
    )


@dataclass
class FreightStartValidity:
    class Meta:
        name = "Freight_Start_Validity"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "pattern": r"\d{4}[-](0[1-9]|1[012])[-](0[1-9]|[12][0-9]|3[01])",
        },
    )


@dataclass
class HandoverPointFlag:
    class Meta:
        name = "Handover_Point_Flag"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: Optional[bool] = field(
        default=None,
        metadata={
            "required": True,
        },
    )


@dataclass
class Latitude:
    class Meta:
        nillable = True
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: Optional[Decimal] = field(
        default=None,
        metadata={
            "total_digits": 14,
            "fraction_digits": 6,
            "nillable": True,
        },
    )


@dataclass
class LocationCode:
    class Meta:
        name = "Location_Code"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "min_length": 1,
            "max_length": 5,
        },
    )


@dataclass
class LocationName:
    class Meta:
        name = "Location_Name"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "min_length": 0,
            "max_length": 255,
        },
    )


@dataclass
class LocationNameAscii:
    class Meta:
        name = "Location_Name_ASCII"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "min_length": 0,
            "max_length": 255,
        },
    )


@dataclass
class Longitude:
    class Meta:
        nillable = True
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: Optional[Decimal] = field(
        default=None,
        metadata={
            "total_digits": 15,
            "fraction_digits": 6,
            "nillable": True,
        },
    )


@dataclass
class ModifiedDate:
    class Meta:
        name = "Modified_Date"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "pattern": r"\d{4}[-](0[1-9]|1[012])[-](0[1-9]|[12][0-9]|3[01])",
        },
    )


@dataclass
class NutsCode:
    class Meta:
        name = "NUTS_Code"
        nillable = True
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: Optional[str] = field(
        default="",
        metadata={
            "max_length": 5,
            "nillable": True,
        },
    )


@dataclass
class PassengerEndValidity:
    class Meta:
        name = "Passenger_End_Validity"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "pattern": r"\d{4}[-](0[1-9]|1[012])[-](0[1-9]|[12][0-9]|3[01])",
        },
    )


@dataclass
class PassengerPossibleFlag:
    class Meta:
        name = "Passenger_Possible_Flag"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: Optional[bool] = field(
        default=None,
        metadata={
            "required": True,
        },
    )


@dataclass
class PassengerStartValidity:
    class Meta:
        name = "Passenger_Start_Validity"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "pattern": r"\d{4}[-](0[1-9]|1[012])[-](0[1-9]|[12][0-9]|3[01])",
        },
    )


@dataclass
class ResponsibleIm:
    class Meta:
        name = "ResponsibleIM"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "min_length": 4,
            "max_length": 4,
        },
    )


@dataclass
class StartValidity:
    class Meta:
        name = "Start_Validity"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "pattern": r"\d{4}[-](0[1-9]|1[012])[-](0[1-9]|[12][0-9]|3[01])",
        },
    )


@dataclass
class PrimaryLocations:
    class Meta:
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    primary_location: List["PrimaryLocations.PrimaryLocation"] = field(
        default_factory=list,
        metadata={
            "name": "Primary_Location",
            "type": "Element",
        },
    )

    @dataclass
    class PrimaryLocation:
        country_iso_code: List[CountryIsoCode2] = field(
            default_factory=list,
            metadata={
                "name": "Country_Iso_Code",
                "type": "Element",
            },
        )
        location_code: List[LocationCode] = field(
            default_factory=list,
            metadata={
                "name": "Location_Code",
                "type": "Element",
            },
        )
        start_validity: List[StartValidity] = field(
            default_factory=list,
            metadata={
                "name": "Start_Validity",
                "type": "Element",
            },
        )
        end_validity: List[EndValidity] = field(
            default_factory=list,
            metadata={
                "name": "End_Validity",
                "type": "Element",
            },
        )
        responsible_im: List[ResponsibleIm] = field(
            default_factory=list,
            metadata={
                "name": "ResponsibleIM",
                "type": "Element",
            },
        )
        location_name: List[LocationName] = field(
            default_factory=list,
            metadata={
                "name": "Location_Name",
                "type": "Element",
            },
        )
        location_name_ascii: List[LocationNameAscii] = field(
            default_factory=list,
            metadata={
                "name": "Location_Name_ASCII",
                "type": "Element",
            },
        )
        nuts_code: List[NutsCode] = field(
            default_factory=list,
            metadata={
                "name": "NUTS_Code",
                "type": "Element",
                "nillable": True,
            },
        )
        container_handling_flag: List[ContainerHandlingFlag] = field(
            default_factory=list,
            metadata={
                "name": "Container_Handling_Flag",
                "type": "Element",
            },
        )
        handover_point_flag: List[HandoverPointFlag] = field(
            default_factory=list,
            metadata={
                "name": "Handover_Point_Flag",
                "type": "Element",
            },
        )
        freight_possible_flag: List[FreightPossibleFlag] = field(
            default_factory=list,
            metadata={
                "name": "Freight_Possible_Flag",
                "type": "Element",
            },
        )
        freight_start_validity: List[FreightStartValidity] = field(
            default_factory=list,
            metadata={
                "name": "Freight_Start_Validity",
                "type": "Element",
            },
        )
        freight_end_validity: List[FreightEndValidity] = field(
            default_factory=list,
            metadata={
                "name": "Freight_End_Validity",
                "type": "Element",
            },
        )
        passenger_possible_flag: List[PassengerPossibleFlag] = field(
            default_factory=list,
            metadata={
                "name": "Passenger_Possible_Flag",
                "type": "Element",
            },
        )
        passenger_start_validity: List[PassengerStartValidity] = field(
            default_factory=list,
            metadata={
                "name": "Passenger_Start_Validity",
                "type": "Element",
            },
        )
        passenger_end_validity: List[PassengerEndValidity] = field(
            default_factory=list,
            metadata={
                "name": "Passenger_End_Validity",
                "type": "Element",
            },
        )
        free_text: List[FreeText] = field(
            default_factory=list,
            metadata={
                "name": "Free_Text",
                "type": "Element",
                "nillable": True,
            },
        )
        latitude: List[Latitude] = field(
            default_factory=list,
            metadata={
                "name": "Latitude",
                "type": "Element",
                "nillable": True,
            },
        )
        longitude: List[Longitude] = field(
            default_factory=list,
            metadata={
                "name": "Longitude",
                "type": "Element",
                "nillable": True,
            },
        )
        active_flag: List[ActiveFlag] = field(
            default_factory=list,
            metadata={
                "name": "Active_Flag",
                "type": "Element",
            },
        )
        add_date: List[AddDate] = field(
            default_factory=list,
            metadata={
                "name": "Add_Date",
                "type": "Element",
            },
        )
        modified_date: List[ModifiedDate] = field(
            default_factory=list,
            metadata={
                "name": "Modified_Date",
                "type": "Element",
            },
        )
