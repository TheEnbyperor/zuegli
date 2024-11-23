from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDate

from main.rsp.gen.apd.common_simple_types_v1_3 import MaritalStatusType

__NAMESPACE__ = "http://www.govtalk.gov.uk/people/PersonDescriptives"


@dataclass
class PersonNameStructure:
    """
    This mirrors the CitizenNameStructure in the AddressAndPersonalDetails
    namespace and supersedes it.
    """

    person_name_title: List[str] = field(
        default_factory=list,
        metadata={
            "name": "PersonNameTitle",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
            "min_length": 1,
            "max_length": 35,
            "pattern": r'[A-Za-z0-9\s~!"@#$%&\'\(\)\*\+,\-\./:;<=>\?\[\\\]_\{\}\^£€]*',
        },
    )
    person_given_name: List[str] = field(
        default_factory=list,
        metadata={
            "name": "PersonGivenName",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
            "min_length": 1,
            "max_length": 35,
            "pattern": r'[A-Za-z0-9\s~!"@#$%&\'\(\)\*\+,\-\./:;<=>\?\[\\\]_\{\}\^£€]*',
        },
    )
    person_family_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "PersonFamilyName",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
            "required": True,
            "min_length": 1,
            "max_length": 35,
            "pattern": r'[A-Za-z0-9\s~!"@#$%&\'\(\)\*\+,\-\./:;<=>\?\[\\\]_\{\}\^£€]*',
        },
    )
    person_name_suffix: List[str] = field(
        default_factory=list,
        metadata={
            "name": "PersonNameSuffix",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
            "min_length": 1,
            "max_length": 35,
            "pattern": r'[A-Za-z0-9\s~!"@#$%&\'\(\)\*\+,\-\./:;<=>\?\[\\\]_\{\}\^£€]*',
        },
    )
    person_requested_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "PersonRequestedName",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
            "min_length": 1,
            "max_length": 70,
            "pattern": r'[A-Za-z0-9\s~!"@#$%&\'\(\)\*\+,\-\./:;<=>\?\[\\\]_\{\}\^£€]*',
        },
    )


class VerificationLevelType(Enum):
    LEVEL_0 = "Level 0"
    LEVEL_1 = "Level 1"
    LEVEL_2 = "Level 2"
    LEVEL_3 = "Level 3"


@dataclass
class PersonBirthDateStructure:
    person_birth_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "PersonBirthDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
            "required": True,
        },
    )
    verification_level: Optional[VerificationLevelType] = field(
        default=None,
        metadata={
            "name": "VerificationLevel",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
        },
    )


@dataclass
class PersonDeathDateStructure:
    person_death_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "PersonDeathDate",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
            "required": True,
        },
    )
    verification_level: Optional[VerificationLevelType] = field(
        default=None,
        metadata={
            "name": "VerificationLevel",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
        },
    )


@dataclass
class PersonMaritalStatus:
    value: Optional[MaritalStatusType] = field(
        default=None,
        metadata={
            "required": True,
        },
    )
    verification_level: Optional[VerificationLevelType] = field(
        default=None,
        metadata={
            "name": "VerificationLevel",
            "type": "Attribute",
        },
    )


@dataclass
class PersonMaritalStatusStructure:
    marital_status: Optional[MaritalStatusType] = field(
        default=None,
        metadata={
            "name": "MaritalStatus",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
            "required": True,
        },
    )
    verification_level: Optional[VerificationLevelType] = field(
        default=None,
        metadata={
            "name": "VerificationLevel",
            "type": "Element",
            "namespace": "http://www.govtalk.gov.uk/people/PersonDescriptives",
        },
    )
