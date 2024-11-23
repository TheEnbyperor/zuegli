from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDate, XmlDateTime, XmlTime

from main.rsp.gen.apd.address_types_v2_0 import (
    UkaddressStructure,
    UkpostalAddressStructure,
)

__NAMESPACE__ = "http://nationalrail.co.uk/xml/common"


@dataclass
class AnnotationContent:
    """Annotation content model.

    Currently only allows paragraphs with optional URLs.
    """

    note: List[str] = field(
        default_factory=list,
        metadata={
            "name": "Note",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "min_occurs": 1,
        },
    )


@dataclass
class AtocListStructure:
    """
    An list of toc codes.
    """

    toc_ref: List[str] = field(
        default_factory=list,
        metadata={
            "name": "TocRef",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "min_occurs": 1,
            "pattern": r"[A-Z]{1}[A-Z0-9]{1}",
        },
    )


class BbcRegionEnumeration(Enum):
    """
    The list of BBC Region codes.
    """

    BM = "BM"
    BS = "BS"
    CB = "CB"
    GB = "GB"
    HL = "HL"
    LDN = "LDN"
    LS = "LS"
    MR = "MR"
    NC = "NC"
    NO = "NO"
    NT = "NT"
    OX = "OX"
    PY = "PY"
    SCOTLAND = "SCOTLAND"
    SO = "SO"
    TW = "TW"
    WALES = "WALES"


@dataclass
class ChangeHistoryStructure:
    """
    Describes the last change made to this document.

    :ivar changed_by: Name of person who last changed this information.
    :ivar last_changed_date: Date and time of last alteration.
    """

    changed_by: Optional["ChangeHistoryStructure.ChangedBy"] = field(
        default=None,
        metadata={
            "name": "ChangedBy",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )
    last_changed_date: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "LastChangedDate",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )

    @dataclass
    class ChangedBy:
        value: str = field(
            default="",
            metadata={
                "required": True,
            },
        )
        toc_affiliation: Optional[str] = field(
            default=None,
            metadata={
                "name": "tocAffiliation",
                "type": "Attribute",
                "pattern": r"[A-Z]{1}[A-Z0-9]{1}",
            },
        )


@dataclass
class ClosedTimeRangeStructure:
    """A range of times.

    Both start and end time are required.

    :ivar start_time: The (inclusive) start time.
    :ivar end_time: The (inclusive) end time.
    """

    start_time: Optional[XmlTime] = field(
        default=None,
        metadata={
            "name": "StartTime",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )
    end_time: Optional[XmlTime] = field(
        default=None,
        metadata={
            "name": "EndTime",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )


class CoinsOrCardsEnumeration(Enum):
    """
    Defines the kind of input for a telephone.
    """

    CARDS = "Cards"
    COINS = "Coins"
    CARDS_AND_COINS = "CardsAndCoins"


@dataclass
class HalfOpenDateRangeStructure:
    """A range of dates.

    The start date is required, but the end date is not.

    :ivar start_date: The (inclusive) start date.
    :ivar end_date: The (inclusive) end date. If omitted, the range end
        is open-ended, that is, it should be interpreted as "forever".
    """

    start_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "StartDate",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )
    end_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "EndDate",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


@dataclass
class HalfOpenTimeRangeStructure:
    """A range of times.

    Start time must be specified, end time is optional.

    :ivar start_time: The (inclusive) start time.
    :ivar end_time: The (inclusive) end time. If omitted, the range end
        is open-ended, that is, it should be interpreted as "forever".
    """

    start_time: Optional[XmlTime] = field(
        default=None,
        metadata={
            "name": "StartTime",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )
    end_time: Optional[XmlTime] = field(
        default=None,
        metadata={
            "name": "EndTime",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


@dataclass
class HalfOpenTimestampRangeStructure:
    """Data Type for a  range of date times.

    Start time must be specified, end time is optional.

    :ivar start_time: The (inclusive) start time stamp.
    :ivar end_time: The (inclusive) end time stamp. If omitted, the
        range end is open-ended, that is, it should be interpreted as
        "forever".
    """

    start_time: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "StartTime",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )
    end_time: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "EndTime",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


class PlatformCoverageEnumeration(Enum):
    """
    Rough indication of platform coverage.
    """

    YES = "Yes"
    PARTIAL = "Partial"
    NO = "No"
    UNKNOWN = "Unknown"


@dataclass
class StationGroupListStructure:
    """
    A list of station groups.
    """

    station_group_ref: List[str] = field(
        default_factory=list,
        metadata={
            "name": "StationGroupRef",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "min_occurs": 1,
        },
    )


@dataclass
class StationListStructure:
    """
    A list of stations.
    """

    station_ref: List[str] = field(
        default_factory=list,
        metadata={
            "name": "StationRef",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "min_occurs": 1,
            "length": 3,
            "pattern": r"[A-Z]{3}",
        },
    )


@dataclass
class TelephoneNumberStructure:
    """
    A telephone number, using GovTalk constructs.

    :ivar tel_national_number: Full telephone number including STD
        prefix
    :ivar tel_extension_number: Any additional extension number.
    :ivar tel_country_code: Two character country prefix, e.g. 44 for
        UK.
    """

    tel_national_number: Optional[str] = field(
        default=None,
        metadata={
            "name": "TelNationalNumber",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
            "pattern": r"[0-9 \-]{1,20}",
        },
    )
    tel_extension_number: Optional[str] = field(
        default=None,
        metadata={
            "name": "TelExtensionNumber",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "pattern": r"[0-9]{1,6}",
        },
    )
    tel_country_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "TelCountryCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "pattern": r"[0-9]{1,3}",
        },
    )


@dataclass
class TravelcardsStructure:
    """
    Information about Travelcards.

    :ivar travelcard_zone: The London Travelcard zone in which this
        station lies.
    """

    travelcard_zone: List[str] = field(
        default_factory=list,
        metadata={
            "name": "TravelcardZone",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


@dataclass
class AnnotatedStructure:
    """
    Abstract base type for types that can be annotated.
    """

    annotation: Optional[AnnotationContent] = field(
        default=None,
        metadata={
            "name": "Annotation",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


@dataclass
class DailyOpeningHoursStructure:
    """
    Specifies hours of opening on a specified day.

    :ivar twenty_four_hours: Open 24hrs on the specified days (defined
        as 00:00 until 23:59)
    :ivar open_period: Each time range indicates an open period.
        Multiple ranges can be used to indicate separate opening hours
        in the morning and afternoon.
    :ivar unavailable: Not available on this specified day.
    """

    twenty_four_hours: Optional[bool] = field(
        default=None,
        metadata={
            "name": "TwentyFourHours",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    open_period: List[ClosedTimeRangeStructure] = field(
        default_factory=list,
        metadata={
            "name": "OpenPeriod",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    unavailable: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Unavailable",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


@dataclass
class PostalAddressStructure:
    """
    :ivar postal_address: Address of  the station based on apd standard
        apd:UKAddressStructure 5 line address and postcode .
    """

    postal_address: Optional[UkaddressStructure] = field(
        default=None,
        metadata={
            "name": "PostalAddress",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


@dataclass
class TelephoneStructure:
    """
    :ivar exists: Does the station have telephones?
    :ivar usage_type: How is it operated? With coins or cards?
    """

    exists: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Exists",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )
    usage_type: Optional[CoinsOrCardsEnumeration] = field(
        default=None,
        metadata={
            "name": "UsageType",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


@dataclass
class ContactDetailsStructure(AnnotatedStructure):
    """
    Methods of contacting a TOC service.

    :ivar primary_telephone_number: Mandatory public telephone number
        for this service.
    :ivar alternate_public_telephone_numbers: Alternate telephone
        numbers available to the public. For example, a national number
        rather than an 0870 number.
    :ivar alternate_internal_telephone_numbers: Alternate telephone
        numbers only available to NRE staff.
    :ivar fax_number: A fax number for this service. Always publicly
        available.
    :ivar primary_minicom_number: A minicom number for this service.
        Always publicly available.
    :ivar alternate_minicom_number: An alternate minicom number for this
        service. Always publicly available. For example, a national
        number rather than an 0870 number.
    :ivar primary_textphone_number: A textphone number for this service.
        Always publicly available.
    :ivar alternate_textphone_number: An textphone number for this
        service. Always publicly available. For example, a national
        number rather than an 0870 number.
    :ivar postal_address: Publicly available postal address of the
        service. Defaults to the TOC Head office address if omitted.
    :ivar email_address: Publicly available email address for this
        service.
    :ivar alternative_email_address: Alternative email address available
        to NRE staff.
    :ivar url: Publicly available web site for this service.
    """

    primary_telephone_number: Optional[TelephoneNumberStructure] = field(
        default=None,
        metadata={
            "name": "PrimaryTelephoneNumber",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    alternate_public_telephone_numbers: Optional[
        "ContactDetailsStructure.AlternatePublicTelephoneNumbers"
    ] = field(
        default=None,
        metadata={
            "name": "AlternatePublicTelephoneNumbers",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    alternate_internal_telephone_numbers: Optional[
        "ContactDetailsStructure.AlternateInternalTelephoneNumbers"
    ] = field(
        default=None,
        metadata={
            "name": "AlternateInternalTelephoneNumbers",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    fax_number: Optional[TelephoneNumberStructure] = field(
        default=None,
        metadata={
            "name": "FaxNumber",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    primary_minicom_number: Optional[TelephoneNumberStructure] = field(
        default=None,
        metadata={
            "name": "PrimaryMinicomNumber",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    alternate_minicom_number: Optional[TelephoneNumberStructure] = field(
        default=None,
        metadata={
            "name": "AlternateMinicomNumber",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    primary_textphone_number: Optional[TelephoneNumberStructure] = field(
        default=None,
        metadata={
            "name": "PrimaryTextphoneNumber",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    alternate_textphone_number: Optional[TelephoneNumberStructure] = field(
        default=None,
        metadata={
            "name": "AlternateTextphoneNumber",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    postal_address: Optional[UkpostalAddressStructure] = field(
        default=None,
        metadata={
            "name": "PostalAddress",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    email_address: Optional[str] = field(
        default=None,
        metadata={
            "name": "EmailAddress",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "pattern": r"[0-9A-Za-z'\.\-_]{1,127}@[0-9A-Za-z'\.\-_]{1,127}",
        },
    )
    alternative_email_address: Optional[str] = field(
        default=None,
        metadata={
            "name": "AlternativeEmailAddress",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "pattern": r"[0-9A-Za-z'\.\-_]{1,127}@[0-9A-Za-z'\.\-_]{1,127}",
        },
    )
    url: Optional[str] = field(
        default=None,
        metadata={
            "name": "Url",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )

    @dataclass
    class AlternatePublicTelephoneNumbers:
        telephone_number: List[TelephoneNumberStructure] = field(
            default_factory=list,
            metadata={
                "name": "TelephoneNumber",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
                "min_occurs": 1,
            },
        )

    @dataclass
    class AlternateInternalTelephoneNumbers:
        telephone_number: List[TelephoneNumberStructure] = field(
            default_factory=list,
            metadata={
                "name": "TelephoneNumber",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
                "min_occurs": 1,
            },
        )


@dataclass
class CrsCodeListStructure(AnnotatedStructure):
    """
    An annotated list of station CRS codes.

    :ivar crs_code: Refers to another station by CRS code.
    """

    crs_code: List[str] = field(
        default_factory=list,
        metadata={
            "name": "CrsCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "length": 3,
            "pattern": r"[A-Z]{3}",
        },
    )


@dataclass
class DayAndTimeAvailabilityStructure:
    """
    Opening hours.

    :ivar day_types: Pattern of days.
    :ivar opening_hours: Hours on the specified day or holiday type when
        the facility is available or unavailable.
    """

    day_types: Optional["DayAndTimeAvailabilityStructure.DayTypes"] = field(
        default=None,
        metadata={
            "name": "DayTypes",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )
    opening_hours: Optional[DailyOpeningHoursStructure] = field(
        default=None,
        metadata={
            "name": "OpeningHours",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
            "required": True,
        },
    )

    @dataclass
    class DayTypes:
        """
        :ivar monday:
        :ivar tuesday:
        :ivar wednesday:
        :ivar thursday:
        :ivar friday:
        :ivar saturday:
        :ivar sunday:
        :ivar monday_to_friday:
        :ivar monday_to_sunday:
        :ivar weekend: Only Saturday and Sunday
        :ivar all_bank_holidays:
        """

        monday: Optional[bool] = field(
            default=None,
            metadata={
                "name": "Monday",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        tuesday: Optional[bool] = field(
            default=None,
            metadata={
                "name": "Tuesday",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        wednesday: Optional[bool] = field(
            default=None,
            metadata={
                "name": "Wednesday",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        thursday: Optional[bool] = field(
            default=None,
            metadata={
                "name": "Thursday",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        friday: Optional[bool] = field(
            default=None,
            metadata={
                "name": "Friday",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        saturday: Optional[bool] = field(
            default=None,
            metadata={
                "name": "Saturday",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        sunday: Optional[bool] = field(
            default=None,
            metadata={
                "name": "Sunday",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        monday_to_friday: Optional[bool] = field(
            default=None,
            metadata={
                "name": "MondayToFriday",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        monday_to_sunday: Optional[bool] = field(
            default=None,
            metadata={
                "name": "MondayToSunday",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        weekend: Optional[bool] = field(
            default=None,
            metadata={
                "name": "Weekend",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )
        all_bank_holidays: Optional[bool] = field(
            default=None,
            metadata={
                "name": "AllBankHolidays",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/common",
            },
        )


@dataclass
class OpeningHoursStructure(AnnotatedStructure):
    """
    Determines the opening hours of a service.

    :ivar day_and_time_availability: Each DayAndTimeAvailability element
        provides the opening hours for a particular range of days.
    """

    day_and_time_availability: List[DayAndTimeAvailabilityStructure] = field(
        default_factory=list,
        metadata={
            "name": "DayAndTimeAvailability",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


@dataclass
class AvailableFacilityStructure(AnnotatedStructure):
    """
    Whether a specified facility is available, and when it is open (if applicable).

    :ivar open: Opening hours of this facility.
    :ivar available: A value of true indicates that opening hours are
        unknown or not applicable.
    :ivar location:
    """

    open: Optional[OpeningHoursStructure] = field(
        default=None,
        metadata={
            "name": "Open",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    available: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Available",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    location: Optional[AnnotationContent] = field(
        default=None,
        metadata={
            "name": "Location",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )


@dataclass
class ServiceStructure(AnnotatedStructure):
    """
    Information about a specific customer service.

    :ivar contact_details:
    :ivar available: Some services do not have specific opening hours.
    :ivar open:
    :ivar operator_name:
    """

    contact_details: Optional[ContactDetailsStructure] = field(
        default=None,
        metadata={
            "name": "ContactDetails",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    available: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Available",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    open: Optional[OpeningHoursStructure] = field(
        default=None,
        metadata={
            "name": "Open",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
    operator_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "OperatorName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/common",
        },
    )
