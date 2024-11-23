from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDate

__NAMESPACE__ = "http://www.govtalk.gov.uk/people/bs7666"


@dataclass
class AonrangeStructure:
    """
    Numeric and optional alpha suffix for start and end numbers.
    """

    class Meta:
        name = "AONrangeStructure"

    number: Optional[int] = field(
        default=None,
        metadata={
            "name": "Number",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "max_inclusive": 9999,
        },
    )
    suffix: Optional[str] = field(
        default=None,
        metadata={
            "name": "Suffix",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_length": 1,
            "max_length": 1,
            "pattern": r"[A-Z]",
        },
    )


@dataclass
class AdministrativeArea:
    class Meta:
        namespace = "http://www.govtalk.gov.uk/people/bs7666"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "min_length": 1,
            "max_length": 30,
        },
    )


class BlpupolygonStructurePolygonType(Enum):
    H = "H"


@dataclass
class CoordinateStructure:
    """
    Coordinate Point based on UK National Grid.

    :ivar x: Easting Field
    :ivar y: Northing Field
    """

    x: Optional[int] = field(
        default=None,
        metadata={
            "name": "X",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_inclusive": 0,
            "max_inclusive": 9999999,
        },
    )
    y: Optional[int] = field(
        default=None,
        metadata={
            "name": "Y",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_inclusive": 0,
            "max_inclusive": 9999999,
        },
    )


@dataclass
class Locality:
    class Meta:
        namespace = "http://www.govtalk.gov.uk/people/bs7666"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "min_length": 1,
            "max_length": 35,
        },
    )


class LogicalStatusType(Enum):
    """
    Logical Status values 1 = Approved preferred 2 = Approved alternative (LPI
    Only) 3 = Alternative (LPI Only) 5 = Candidate 6 = Provisional 8 = Historical 9
    = Rejected.
    """

    VALUE_1 = 1
    VALUE_2 = 2
    VALUE_3 = 3
    VALUE_5 = 5
    VALUE_6 = 6
    VALUE_8 = 8
    VALUE_9 = 9


class ProvenanceCodeType(Enum):
    """
    Provenance Code values T = Registered land title L = Unregistered land title F
    = Formal tenancy agreement R = Rental agreement P = Physical features O =
    Occupancy U = Use.
    """

    T = "T"
    L = "L"
    F = "F"
    R = "R"
    P = "P"
    O = "O"
    U = "U"


class RepresentativePointCodeType(Enum):
    """
    Representative Point Code values 1 = Visual centre 2 = General internal point 3
    = South-west corner of 100m grid square 4 = Start point of the referenced
    street.
    """

    VALUE_1 = 1
    VALUE_2 = 2
    VALUE_3 = 3
    VALUE_4 = 4
    VALUE_5 = 5
    VALUE_9 = 9


class StreetReferenceTypeType(Enum):
    VALUE_1 = 1
    VALUE_2 = 2
    VALUE_3 = 3
    VALUE_4 = 4


@dataclass
class Town:
    class Meta:
        namespace = "http://www.govtalk.gov.uk/people/bs7666"

    value: str = field(
        default="",
        metadata={
            "required": True,
            "min_length": 1,
            "max_length": 30,
        },
    )


@dataclass
class UniquePropertyReferenceNumber:
    class Meta:
        namespace = "http://www.govtalk.gov.uk/people/bs7666"

    value: Optional[int] = field(
        default=None,
        metadata={
            "required": True,
            "min_inclusive": 1,
            "max_inclusive": 999999999999,
        },
    )


@dataclass
class Aonstructure:
    """
    Replacement for PAONtype and SAONtype.
    """

    class Meta:
        name = "AONstructure"

    start_range: Optional[AonrangeStructure] = field(
        default=None,
        metadata={
            "name": "StartRange",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    end_range: Optional[AonrangeStructure] = field(
        default=None,
        metadata={
            "name": "EndRange",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    description: List[str] = field(
        default_factory=list,
        metadata={
            "name": "Description",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_occurs": 1,
            "max_occurs": 2,
            "min_length": 1,
            "max_length": 90,
            "pattern": r"[a-zA-Z0-9:;<=>\?@%&'\(\)\*\+,\-\. ]{0,90}",
            "sequence": 1,
        },
    )


@dataclass
class BlpupolygonStructure:
    """
    :ivar polygon_id:
    :ivar polygon_type: H to represent a hole or not present
    :ivar vertices:
    :ivar external_ref:
    """

    class Meta:
        name = "BLPUpolygonStructure"

    polygon_id: Optional[int] = field(
        default=None,
        metadata={
            "name": "PolygonID",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_inclusive": 1,
            "max_inclusive": 99,
        },
    )
    polygon_type: Optional[BlpupolygonStructurePolygonType] = field(
        default=None,
        metadata={
            "name": "PolygonType",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    vertices: List[CoordinateStructure] = field(
        default_factory=list,
        metadata={
            "name": "Vertices",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    external_ref: Optional[int] = field(
        default=None,
        metadata={
            "name": "ExternalRef",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )


@dataclass
class ElementaryStreetUnitStructure:
    esuidentity: Optional[str] = field(
        default=None,
        metadata={
            "name": "ESUidentity",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "pattern": r"[0-9]{14}",
        },
    )
    esuversion: Optional[int] = field(
        default=None,
        metadata={
            "name": "ESUversion",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_inclusive": 1,
            "max_inclusive": 9999,
        },
    )
    esuentry_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ESUentryDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    esuclosure_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ESUclosureDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    start_coordinate: Optional[CoordinateStructure] = field(
        default=None,
        metadata={
            "name": "StartCoordinate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    end_coordinate: Optional[CoordinateStructure] = field(
        default=None,
        metadata={
            "name": "EndCoordinate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    tolerance: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "Tolerance",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_inclusive": Decimal("0"),
        },
    )
    intermediate_coord: List[CoordinateStructure] = field(
        default_factory=list,
        metadata={
            "name": "IntermediateCoord",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )


@dataclass
class StreetDescriptiveIdentifierStructure:
    street_description: Optional[str] = field(
        default=None,
        metadata={
            "name": "StreetDescription",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_length": 1,
            "max_length": 100,
        },
    )
    locality: Optional[Locality] = field(
        default=None,
        metadata={
            "name": "Locality",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    town: List[Town] = field(
        default_factory=list,
        metadata={
            "name": "Town",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "max_occurs": 2,
        },
    )
    administrative_area: List[AdministrativeArea] = field(
        default_factory=list,
        metadata={
            "name": "AdministrativeArea",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "max_occurs": 4,
        },
    )


@dataclass
class BlpuextentStructure:
    """
    :ivar source_description: Description of Source of BLPU Extent
    :ivar extent_entry_date:
    :ivar extent_source_date:
    :ivar extent_start_date:
    :ivar extent_end_date:
    :ivar extent_last_update_date:
    :ivar extent_definition:
    """

    class Meta:
        name = "BLPUextentStructure"

    source_description: Optional[str] = field(
        default=None,
        metadata={
            "name": "SourceDescription",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_length": 1,
            "max_length": 50,
        },
    )
    extent_entry_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ExtentEntryDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    extent_source_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ExtentSourceDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    extent_start_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ExtentStartDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    extent_end_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ExtentEndDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    extent_last_update_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ExtentLastUpdateDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    extent_definition: List[BlpupolygonStructure] = field(
        default_factory=list,
        metadata={
            "name": "ExtentDefinition",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_occurs": 1,
        },
    )


@dataclass
class BsaddressStructure:
    """
    :ivar saon: Secondary Addressable Object
    :ivar paon: Primary Addressable Object
    :ivar street_description:
    :ivar unique_street_reference_number:
    :ivar locality:
    :ivar town:
    :ivar administrative_area:
    :ivar post_town:
    :ivar post_code:
    :ivar unique_property_reference_number:
    """

    class Meta:
        name = "BSaddressStructure"

    saon: Optional[Aonstructure] = field(
        default=None,
        metadata={
            "name": "SAON",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    paon: Optional[Aonstructure] = field(
        default=None,
        metadata={
            "name": "PAON",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    street_description: Optional[str] = field(
        default=None,
        metadata={
            "name": "StreetDescription",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_length": 1,
            "max_length": 100,
        },
    )
    unique_street_reference_number: Optional[int] = field(
        default=None,
        metadata={
            "name": "UniqueStreetReferenceNumber",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_inclusive": 1,
            "max_inclusive": 99999999,
        },
    )
    locality: Optional[Locality] = field(
        default=None,
        metadata={
            "name": "Locality",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    town: List[Town] = field(
        default_factory=list,
        metadata={
            "name": "Town",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "max_occurs": 2,
        },
    )
    administrative_area: List[AdministrativeArea] = field(
        default_factory=list,
        metadata={
            "name": "AdministrativeArea",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "max_occurs": 4,
        },
    )
    post_town: Optional[str] = field(
        default=None,
        metadata={
            "name": "PostTown",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_length": 1,
            "max_length": 30,
        },
    )
    post_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "PostCode",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "pattern": r"[A-Z]{1,2}[0-9R][0-9A-Z]? [0-9][A-Z-[CIKMOV]]{2}",
        },
    )
    unique_property_reference_number: Optional[int] = field(
        default=None,
        metadata={
            "name": "UniquePropertyReferenceNumber",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_inclusive": 1,
            "max_inclusive": 999999999999,
        },
    )


@dataclass
class StreetStructure:
    street_reference_type: Optional[StreetReferenceTypeType] = field(
        default=None,
        metadata={
            "name": "StreetReferenceType",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    start_coordinate: Optional[CoordinateStructure] = field(
        default=None,
        metadata={
            "name": "StartCoordinate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    end_coordinate: Optional[CoordinateStructure] = field(
        default=None,
        metadata={
            "name": "EndCoordinate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    tolerance: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "Tolerance",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_inclusive": Decimal("0"),
        },
    )
    street_version_number: Optional[int] = field(
        default=None,
        metadata={
            "name": "StreetVersionNumber",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_inclusive": 1,
            "max_inclusive": 9999,
        },
    )
    street_entry_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "StreetEntryDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    street_closure_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "StreetClosureDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    responsible_authority: Optional[int] = field(
        default=None,
        metadata={
            "name": "ResponsibleAuthority",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_inclusive": 1,
            "max_inclusive": 9999,
        },
    )
    descriptive_identifier: Optional[StreetDescriptiveIdentifierStructure] = (
        field(
            default=None,
            metadata={
                "name": "DescriptiveIdentifier",
                "type": "Element",
                "namespace": "http://www.govtalk.gov.uk/people/bs7666",
                "required": True,
            },
        )
    )
    street_alias: Optional[StreetDescriptiveIdentifierStructure] = field(
        default=None,
        metadata={
            "name": "StreetAlias",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    street_cross_references: Optional[
        "StreetStructure.StreetCrossReferences"
    ] = field(
        default=None,
        metadata={
            "name": "StreetCrossReferences",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    usrn: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "min_inclusive": 1,
            "max_inclusive": 99999999,
        },
    )

    @dataclass
    class StreetCrossReferences:
        unique_street_reference_numbers: List[int] = field(
            default_factory=list,
            metadata={
                "name": "UniqueStreetReferenceNumbers",
                "type": "Element",
                "namespace": "http://www.govtalk.gov.uk/people/bs7666",
                "min_inclusive": 1,
                "max_inclusive": 99999999,
                "tokens": True,
            },
        )
        elementary_street_unit: List[ElementaryStreetUnitStructure] = field(
            default_factory=list,
            metadata={
                "name": "ElementaryStreetUnit",
                "type": "Element",
                "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            },
        )


@dataclass
class Bs7666Address(BsaddressStructure):
    class Meta:
        name = "BS7666Address"
        namespace = "http://www.govtalk.gov.uk/people/bs7666"


@dataclass
class LandAndPropertyIdentifierStructure:
    paon: Optional[Aonstructure] = field(
        default=None,
        metadata={
            "name": "PAON",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    saon: Optional[Aonstructure] = field(
        default=None,
        metadata={
            "name": "SAON",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    post_town: Optional[str] = field(
        default=None,
        metadata={
            "name": "PostTown",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_length": 1,
            "max_length": 30,
        },
    )
    post_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "PostCode",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "pattern": r"[A-Z]{1,2}[0-9R][0-9A-Z]? [0-9][A-Z-[CIKMOV]]{2}",
        },
    )
    level: Optional[str] = field(
        default=None,
        metadata={
            "name": "Level",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_length": 1,
            "max_length": 30,
        },
    )
    logical_status: Optional[LogicalStatusType] = field(
        default=None,
        metadata={
            "name": "LogicalStatus",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    official_address_marker: Optional[bool] = field(
        default=None,
        metadata={
            "name": "OfficialAddressMarker",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    lpistart_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "LPIstartDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    lpientry_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "LPIentryDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    lpiend_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "LPIendDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    lpilast_update_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "LPIlastUpdateDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    street: Optional[StreetStructure] = field(
        default=None,
        metadata={
            "name": "Street",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    usrn: Optional[int] = field(
        default=None,
        metadata={
            "name": "USRN",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_inclusive": 1,
            "max_inclusive": 99999999,
        },
    )


@dataclass
class ProvenanceStructure:
    provenance_code: Optional[ProvenanceCodeType] = field(
        default=None,
        metadata={
            "name": "ProvenanceCode",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    annotation: Optional[str] = field(
        default=None,
        metadata={
            "name": "Annotation",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    prov_entry_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ProvEntryDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    prov_start_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ProvStartDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    prov_end_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ProvEndDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    prov_last_update_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "ProvLastUpdateDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    blpuextent: Optional[BlpuextentStructure] = field(
        default=None,
        metadata={
            "name": "BLPUextent",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )


@dataclass
class BasicLandAndPropertyUnitStructure:
    unique_property_reference_number: Optional[
        UniquePropertyReferenceNumber
    ] = field(
        default=None,
        metadata={
            "name": "UniquePropertyReferenceNumber",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    custodian_code: Optional[int] = field(
        default=None,
        metadata={
            "name": "CustodianCode",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
            "min_inclusive": 1,
            "max_inclusive": 9999,
        },
    )
    representative_point_code: Optional[RepresentativePointCodeType] = field(
        default=None,
        metadata={
            "name": "RepresentativePointCode",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    logical_status: Optional[LogicalStatusType] = field(
        default=None,
        metadata={
            "name": "LogicalStatus",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    grid_reference: Optional[CoordinateStructure] = field(
        default=None,
        metadata={
            "name": "GridReference",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    blpuentry_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "BLPUentryDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    blpustart_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "BLPUstartDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    blpuend_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "BLPUendDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
        },
    )
    blpulast_update_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "BLPUlastUpdateDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "required": True,
        },
    )
    land_and_property_identifier: List[LandAndPropertyIdentifierStructure] = (
        field(
            default_factory=list,
            metadata={
                "name": "LandAndPropertyIdentifier",
                "type": "Element",
                "namespace": "http://www.govtalk.gov.uk/people/bs7666",
                "min_occurs": 1,
            },
        )
    )
    provenance: List[ProvenanceStructure] = field(
        default_factory=list,
        metadata={
            "name": "Provenance",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/bs7666",
            "min_occurs": 1,
        },
    )


@dataclass
class Bs7666Blpu(BasicLandAndPropertyUnitStructure):
    class Meta:
        name = "BS7666BLPU"
        namespace = "http://www.govtalk.gov.uk/people/bs7666"
