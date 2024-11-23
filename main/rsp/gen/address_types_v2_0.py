from dataclasses import dataclass, field
from typing import List, Optional

from main.rsp.gen.bs7666_v2_0 import BsaddressStructure

__NAMESPACE__ = "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails"


@dataclass
class InternationalAddressStructure:
    int_address_line: List[str] = field(
        default_factory=list,
        metadata={
            "name": "IntAddressLine",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
            "min_occurs": 2,
            "max_occurs": 5,
            "min_length": 1,
            "max_length": 35,
            "pattern": r'[A-Za-z0-9\s~!"@#$%&\'\(\)\*\+,\-\./:;<=>\?\[\\\]_\{\}\^£€]*',
        },
    )
    country: List[str] = field(
        default_factory=list,
        metadata={
            "name": "Country",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
            "min_occurs": 1,
            "max_occurs": 2,
            "min_length": 1,
            "max_length": 35,
            "pattern": r'[A-Za-z0-9\s~!"@#$%&\'\(\)\*\+,\-\./:;<=>\?\[\\\]_\{\}\^£€]*',
            "sequence": 1,
        },
    )
    international_post_code: List[str] = field(
        default_factory=list,
        metadata={
            "name": "InternationalPostCode",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
            "min_occurs": 1,
            "max_occurs": 2,
            "min_length": 1,
            "max_length": 35,
            "pattern": r'[A-Za-z0-9\s~!"@#$%&\'\(\)\*\+,\-\./:;<=>\?\[\\\]_\{\}\^£€]*',
            "sequence": 1,
        },
    )


@dataclass
class UkpostalAddressStructure:
    class Meta:
        name = "UKPostalAddressStructure"

    line: List[str] = field(
        default_factory=list,
        metadata={
            "name": "Line",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
            "min_occurs": 2,
            "max_occurs": 5,
            "min_length": 1,
            "max_length": 35,
            "pattern": r'[A-Za-z0-9\s~!"@#$%&\'\(\)\*\+,\-\./:;<=>\?\[\\\]_\{\}\^£€]*',
        },
    )
    post_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "PostCode",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
            "pattern": r"[A-Z]{1,2}[0-9R][0-9A-Z]? [0-9][A-Z-[CIKMOV]]{2}",
        },
    )


@dataclass
class UkaddressStructure:
    """
    Supports BS7666 address types.
    """

    class Meta:
        name = "UKAddressStructure"

    bs7666_address: List[BsaddressStructure] = field(
        default_factory=list,
        metadata={
            "name": "BS7666Address",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
            "max_occurs": 2,
        },
    )
    a_5_line_address: Optional[UkpostalAddressStructure] = field(
        default=None,
        metadata={
            "name": "A_5LineAddress",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
        },
    )
    unique_property_reference_number: Optional[int] = field(
        default=None,
        metadata={
            "name": "UniquePropertyReferenceNumber",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
            "min_inclusive": 1,
            "max_inclusive": 999999999999,
        },
    )
    sort_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "SortCode",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
            "pattern": r"[0-9]{5}",
        },
    )
    walk_sort: Optional[str] = field(
        default=None,
        metadata={
            "name": "WalkSort",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/AddressAndPersonalDetails",
            "pattern": r"[0-9]{8}",
        },
    )
