from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from main.rsp.gen.nre_common_v5_0 import AtocListStructure

__NAMESPACE__ = "http://nationalrail.co.uk/xml/ticket"


@dataclass
class BreakOfJourneyStructure:
    outward_note: Optional[str] = field(
        default=None,
        metadata={
            "name": "OutwardNote",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    return_note: Optional[str] = field(
        default=None,
        metadata={
            "name": "ReturnNote",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )


class ClassEnumeration(Enum):
    FIRST = "First"
    STANDARD = "Standard"
    OTHER = "Other"


@dataclass
class DiscountDetailStructure:
    permitted: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Permitted",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    note: Optional[str] = field(
        default=None,
        metadata={
            "name": "Note",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )


class FareCategoryEnumeration(Enum):
    """
    Fare category types.
    """

    OPEN = "open"
    FLEXIBLE = "flexible"
    RESTRICTED = "restricted"


class SingleReturnEnumeration(Enum):
    """
    Fare category types.
    """

    SINGLE = "Single"
    RETURN = "Return"


@dataclass
class ValidityStructure:
    day_outward: Optional[str] = field(
        default=None,
        metadata={
            "name": "DayOutward",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    day_return: Optional[str] = field(
        default=None,
        metadata={
            "name": "DayReturn",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    time_outward: Optional[str] = field(
        default=None,
        metadata={
            "name": "TimeOutward",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    time_return: Optional[str] = field(
        default=None,
        metadata={
            "name": "TimeReturn",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )


@dataclass
class ApplicableTocsStructure:
    """
    :ivar included_tocs: The ticket type is valid for the specified
        TOCS.
    :ivar excluded_tocs: The ticket type is valid for all TOCs except
        these.
    """

    included_tocs: Optional[AtocListStructure] = field(
        default=None,
        metadata={
            "name": "IncludedTocs",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    excluded_tocs: Optional[AtocListStructure] = field(
        default=None,
        metadata={
            "name": "ExcludedTocs",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )


@dataclass
class DiscountStructure:
    child: Optional[DiscountDetailStructure] = field(
        default=None,
        metadata={
            "name": "Child",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    rail_card: Optional[DiscountDetailStructure] = field(
        default=None,
        metadata={
            "name": "RailCard",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    group: Optional[DiscountDetailStructure] = field(
        default=None,
        metadata={
            "name": "Group",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )


@dataclass
class TicketTypeDescriptionStructure:
    """
    Type for a TicketDescription.

    :ivar ticket_type_identifier: Three character code identifying a
        Ticket Type
    :ivar ticket_type_code: Three character code identifying a Ticket
        Type
    :ivar ticket_type_name: The name of the ticket type.
    :ivar description: The description of the ticket type.
    :ivar class_value: The Class of the ticket.
    :ivar single_return:
    :ivar applicable_tocs: The TOCS who support the ticket.
    :ivar validity: When is the ticket type valid to use.
    :ivar break_of_journey: Breaks in journey that are allowed for by
        the ticket type.
    :ivar fare_category: Information about the Fare Category applicable
        to the ticket type
    :ivar conditions: Any conditions that apply to use the ticket type.
    :ivar availability: When the ticket type is avaliable to purchase.
    :ivar retailing: Information regarding retailing for the ticket
        type.
    :ivar booking_deadlines: Any deadlines for purchasing the ticket
        type.
    :ivar compulsory_reservations: Is it compulsory to make a
        reservation.
    :ivar changes_to_travel_plans: Changes of travel plans allowed for
        by the ticket type.
    :ivar refunds: Refund rules for the ticket type.
    :ivar discount: Refund rules for the ticket type.
    :ivar special_conditions:
    """

    ticket_type_identifier: Optional[str] = field(
        default=None,
        metadata={
            "name": "TicketTypeIdentifier",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
            "required": True,
            "pattern": r"[A-Z0-9]{32}",
        },
    )
    ticket_type_code: List[str] = field(
        default_factory=list,
        metadata={
            "name": "TicketTypeCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
            "min_occurs": 1,
            "pattern": r"[A-Z0-9]{3}",
        },
    )
    ticket_type_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "TicketTypeName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
            "required": True,
        },
    )
    description: Optional[str] = field(
        default=None,
        metadata={
            "name": "Description",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
            "required": True,
        },
    )
    class_value: Optional[ClassEnumeration] = field(
        default=None,
        metadata={
            "name": "Class",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
            "required": True,
        },
    )
    single_return: Optional[SingleReturnEnumeration] = field(
        default=None,
        metadata={
            "name": "SingleReturn",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
            "required": True,
        },
    )
    applicable_tocs: Optional[ApplicableTocsStructure] = field(
        default=None,
        metadata={
            "name": "ApplicableTocs",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    validity: Optional[ValidityStructure] = field(
        default=None,
        metadata={
            "name": "Validity",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    break_of_journey: Optional[BreakOfJourneyStructure] = field(
        default=None,
        metadata={
            "name": "BreakOfJourney",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    fare_category: Optional[FareCategoryEnumeration] = field(
        default=None,
        metadata={
            "name": "FareCategory",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
            "required": True,
        },
    )
    conditions: Optional[str] = field(
        default=None,
        metadata={
            "name": "Conditions",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    availability: Optional[str] = field(
        default=None,
        metadata={
            "name": "Availability",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    retailing: Optional[str] = field(
        default=None,
        metadata={
            "name": "Retailing",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    booking_deadlines: Optional[str] = field(
        default=None,
        metadata={
            "name": "BookingDeadlines",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    compulsory_reservations: Optional[str] = field(
        default=None,
        metadata={
            "name": "CompulsoryReservations",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    changes_to_travel_plans: Optional[str] = field(
        default=None,
        metadata={
            "name": "ChangesToTravelPlans",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    refunds: Optional[str] = field(
        default=None,
        metadata={
            "name": "Refunds",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    discount: Optional[DiscountStructure] = field(
        default=None,
        metadata={
            "name": "Discount",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )
    special_conditions: Optional[str] = field(
        default=None,
        metadata={
            "name": "SpecialConditions",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticket",
        },
    )


@dataclass
class TicketTypeDescription(TicketTypeDescriptionStructure):
    """
    Details of a ticket type as required for the NRE Knowledge Base.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/ticket"


@dataclass
class TicketTypeDescriptionList:
    """
    A list of ticket types.

    :ivar ticket_type_description: Details of a ticket type as required
        for the NRE Knowledge Base.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/ticket"

    ticket_type_description: List[TicketTypeDescription] = field(
        default_factory=list,
        metadata={
            "name": "TicketTypeDescription",
            "type": "Element",
        },
    )
