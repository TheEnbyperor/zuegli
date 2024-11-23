from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

__NAMESPACE__ = "http://nationalrail.co.uk/xml/ticketrestriction"


@dataclass
class RestrictionStructure:
    station_outward: Optional[str] = field(
        default=None,
        metadata={
            "name": "StationOutward",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "length": 3,
        },
    )
    station_return: Optional[str] = field(
        default=None,
        metadata={
            "name": "StationReturn",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "length": 3,
        },
    )
    details_outward: Optional[str] = field(
        default=None,
        metadata={
            "name": "DetailsOutward",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "required": True,
            "min_length": 1,
        },
    )
    details_return: Optional[str] = field(
        default=None,
        metadata={
            "name": "DetailsReturn",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
        },
    )
    comments_outward: Optional[str] = field(
        default=None,
        metadata={
            "name": "CommentsOutward",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
        },
    )
    comments_return: Optional[str] = field(
        default=None,
        metadata={
            "name": "CommentsReturn",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
        },
    )


class TicketRestrictionStructureOutwardDirection(Enum):
    OUTWARD_TRAVEL = "Outward Travel"
    MORNING_TRAVEL = "Morning Travel"
    EASTBOUND_TRAVEL = "Eastbound Travel"
    NORTHBOUND_TRAVEL = "Northbound Travel"
    SOUTHBOUND_TRAVEL = "Southbound Travel"
    WESTBOUND_TRAVEL = "Westbound Travel"
    FROM_LONDON = "From London"
    TOWARDS_LONDON = "Towards London"
    OUTWARD = "Outward"
    RETURN = "Return"


class TicketRestrictionStructureReturnDirection(Enum):
    RETURN_TRAVEL = "Return Travel"
    EVENING_TRAVEL = "Evening Travel"
    WESTBOUND_TRAVEL = "Westbound Travel"
    SOUTHBOUND_TRAVEL = "Southbound Travel"
    NORTHBOUND_TRAVEL = "Northbound Travel"
    EASTBOUND_TRAVEL = "Eastbound Travel"
    FROM_LONDON = "From London"
    TOWARDS_LONDON = "Towards London"
    OUTWARD = "Outward"
    RETURN = "Return"


@dataclass
class TicketRestrictionStructure:
    """
    :ivar name:
    :ivar link_to_detail_page:
    :ivar restriction_code:
    :ivar ticket_restriction_identifier:
    :ivar applicable_days:
    :ivar easement:
    :ivar notes:
    :ivar seasonal_variations:
    :ivar outward_direction:
    :ivar return_direction:
    :ivar return_status:
    :ivar outward_status:
    :ivar restrictions_type:
    :ivar restrictions: Restrictions Wrapper
    """

    name: Optional[str] = field(
        default=None,
        metadata={
            "name": "Name",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "required": True,
            "min_length": 1,
        },
    )
    link_to_detail_page: Optional[str] = field(
        default=None,
        metadata={
            "name": "LinkToDetailPage",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "required": True,
        },
    )
    restriction_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "RestrictionCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "required": True,
            "min_length": 1,
        },
    )
    ticket_restriction_identifier: Optional[str] = field(
        default=None,
        metadata={
            "name": "TicketRestrictionIdentifier",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "required": True,
        },
    )
    applicable_days: Optional[str] = field(
        default=None,
        metadata={
            "name": "ApplicableDays",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "required": True,
            "min_length": 1,
        },
    )
    easement: Optional[str] = field(
        default=None,
        metadata={
            "name": "Easement",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
        },
    )
    notes: Optional[str] = field(
        default=None,
        metadata={
            "name": "Notes",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
        },
    )
    seasonal_variations: Optional[str] = field(
        default=None,
        metadata={
            "name": "SeasonalVariations",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
        },
    )
    outward_direction: Optional[TicketRestrictionStructureOutwardDirection] = (
        field(
            default=None,
            metadata={
                "name": "OutwardDirection",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
                "required": True,
            },
        )
    )
    return_direction: Optional[TicketRestrictionStructureReturnDirection] = (
        field(
            default=None,
            metadata={
                "name": "ReturnDirection",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
                "required": True,
            },
        )
    )
    return_status: Optional[str] = field(
        default=None,
        metadata={
            "name": "ReturnStatus",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
        },
    )
    outward_status: Optional[str] = field(
        default=None,
        metadata={
            "name": "OutwardStatus",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
        },
    )
    restrictions_type: Optional[str] = field(
        default=None,
        metadata={
            "name": "RestrictionsType",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "required": True,
            "pattern": r"2|4",
        },
    )
    restrictions: Optional["TicketRestrictionStructure.Restrictions"] = field(
        default=None,
        metadata={
            "name": "Restrictions",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
            "required": True,
        },
    )

    @dataclass
    class Restrictions:
        """
        :ivar restriction: Restriction's details
        """

        restriction: List[RestrictionStructure] = field(
            default_factory=list,
            metadata={
                "name": "Restriction",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/ticketrestriction",
                "min_occurs": 1,
            },
        )


@dataclass
class TicketRestriction(TicketRestrictionStructure):
    """
    Public Transport Restrictions.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/ticketrestriction"


@dataclass
class TicketRestrictions:
    """
    A list of Ticket Restrictions.

    :ivar ticket_restriction: Public Transport Restrictions.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/ticketrestriction"

    ticket_restriction: List[TicketRestriction] = field(
        default_factory=list,
        metadata={
            "name": "TicketRestriction",
            "type": "Element",
        },
    )
