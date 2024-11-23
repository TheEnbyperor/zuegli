from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from main.rsp.gen.nre_common_v5_0 import (
    AtocListStructure,
    BbcRegionEnumeration,
    ChangeHistoryStructure,
    ContactDetailsStructure,
    HalfOpenDateRangeStructure,
    OpeningHoursStructure,
    StationGroupListStructure,
    StationListStructure,
)

__NAMESPACE__ = "http://nationalrail.co.uk/xml/promotion"


@dataclass
class DayTicketStructure:
    adult: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "Adult",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    child: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "Child",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    railcard: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "Railcard",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    note: Optional[str] = field(
        default=None,
        metadata={
            "name": "Note",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class DiscountDetail:
    ticket_type_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "TicketTypeName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    ticket_type_code: List[str] = field(
        default_factory=list,
        metadata={
            "name": "TicketTypeCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "pattern": r"[A-Z0-9]{3}",
        },
    )
    card_holder: Optional[str] = field(
        default=None,
        metadata={
            "name": "CardHolder",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    accompanying_adult: Optional[str] = field(
        default=None,
        metadata={
            "name": "AccompanyingAdult",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    accompanying_child: Optional[str] = field(
        default=None,
        metadata={
            "name": "AccompanyingChild",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    note: Optional[str] = field(
        default=None,
        metadata={
            "name": "Note",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class InternalInfoStructure:
    """
    A stucture containing details and a Uri.
    """

    issuing_instructions: Optional[str] = field(
        default=None,
        metadata={
            "name": "IssuingInstructions",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    details: Optional[str] = field(
        default=None,
        metadata={
            "name": "Details",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class LinkAndDetailsStructure:
    """
    A stucture containing details and a Uri.
    """

    uri: List[str] = field(
        default_factory=list,
        metadata={
            "name": "Uri",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    details: Optional[str] = field(
        default=None,
        metadata={
            "name": "Details",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class LinkStructure:
    """
    A list of station groups.
    """

    uri: List[str] = field(
        default_factory=list,
        metadata={
            "name": "Uri",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "min_occurs": 1,
        },
    )


@dataclass
class NearestStationStructure:
    """
    A list of stations.
    """

    crs_code: List[str] = field(
        default_factory=list,
        metadata={
            "name": "CrsCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "min_occurs": 1,
            "length": 3,
            "pattern": r"[A-Z]{3}",
        },
    )


@dataclass
class PassengerStructure:
    note: Optional[str] = field(
        default=None,
        metadata={
            "name": "Note",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    min_adults: Optional[int] = field(
        default=None,
        metadata={
            "name": "MinAdults",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    max_adults: Optional[int] = field(
        default=None,
        metadata={
            "name": "MaxAdults",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    min_children: Optional[int] = field(
        default=None,
        metadata={
            "name": "MinChildren",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    max_children: Optional[int] = field(
        default=None,
        metadata={
            "name": "MaxChildren",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class PromoApplicableTocsStructure:
    all_tocs: Optional[bool] = field(
        default=None,
        metadata={
            "name": "AllTocs",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    toc_ref: List[str] = field(
        default_factory=list,
        metadata={
            "name": "TocRef",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "pattern": r"[A-Z]{1}[A-Z0-9]{1}",
        },
    )


@dataclass
class PromotionFareDetailsStructure:
    price: Optional[str] = field(
        default=None,
        metadata={
            "name": "Price",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    details: Optional[str] = field(
        default=None,
        metadata={
            "name": "Details",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class PromotionRailCardStructure:
    """
    A structure containing a RailCard name and its applicability to the promotion.
    """

    rail_card_id: Optional[str] = field(
        default=None,
        metadata={
            "name": "RailCardId",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
        },
    )
    price: Optional[str] = field(
        default=None,
        metadata={
            "name": "Price",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    details: Optional[str] = field(
        default=None,
        metadata={
            "name": "Details",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class SeasonTicketStructure:
    seven_days: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "SevenDays",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    one_month: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "OneMonth",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    three_months: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "ThreeMonths",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    one_year: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "OneYear",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    note: Optional[str] = field(
        default=None,
        metadata={
            "name": "Note",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


class ViewableByEnumeration(Enum):
    """
    Who can see the  promotion viewable  .

    :cvar PUBLIC: Promotion can be seen by the public.
    :cvar INTERNAL: Promotion is not visible to public. Normal Staff
        only promotions are not visible to public
    :cvar XML_FEED: Not available on public or internal, only via XML
        Feed.
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    XML_FEED = "xmlFeed"


@dataclass
class DiscountsAvailableStructure:
    discount_detail: List[DiscountDetail] = field(
        default_factory=list,
        metadata={
            "name": "DiscountDetail",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    plus_bus: Optional[str] = field(
        default=None,
        metadata={
            "name": "PlusBus",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    sleeper_services: Optional[str] = field(
        default=None,
        metadata={
            "name": "SleeperServices",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    other_discounts: Optional[str] = field(
        default=None,
        metadata={
            "name": "OtherDiscounts",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class FlowStructure:
    origin: Optional[str] = field(
        default=None,
        metadata={
            "name": "Origin",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
            "length": 3,
            "pattern": r"[A-Z]{3}",
        },
    )
    destination: Optional[str] = field(
        default=None,
        metadata={
            "name": "Destination",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
            "length": 3,
            "pattern": r"[A-Z]{3}",
        },
    )
    reversible: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Reversible",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
        },
    )
    station: Optional[str] = field(
        default=None,
        metadata={
            "name": "Station",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "length": 3,
            "pattern": r"[A-Z]{3}",
        },
    )
    tocs: Optional[AtocListStructure] = field(
        default=None,
        metadata={
            "name": "Tocs",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class PromotionRailCardListStructure:
    """
    A structure containing a list of railcards and applicability option values.
    """

    promotion_rail_card: List[PromotionRailCardStructure] = field(
        default_factory=list,
        metadata={
            "name": "PromotionRailCard",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "min_occurs": 1,
        },
    )


@dataclass
class ExceptionsStructure:
    exception: List[FlowStructure] = field(
        default_factory=list,
        metadata={
            "name": "Exception",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "min_occurs": 1,
        },
    )


@dataclass
class FlowsStructure:
    flow: List[FlowStructure] = field(
        default_factory=list,
        metadata={
            "name": "Flow",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "min_occurs": 1,
        },
    )


@dataclass
class ProductTypeStructure:
    name: Optional[str] = field(
        default=None,
        metadata={
            "name": "Name",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    valid: Optional[str] = field(
        default=None,
        metadata={
            "name": "Valid",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    adult_price: Optional[str] = field(
        default=None,
        metadata={
            "name": "AdultPrice",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    child_price: Optional[str] = field(
        default=None,
        metadata={
            "name": "ChildPrice",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    family_price: Optional[str] = field(
        default=None,
        metadata={
            "name": "FamilyPrice",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    group_price: Optional[str] = field(
        default=None,
        metadata={
            "name": "GroupPrice",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    staff_discount_adult: Optional[str] = field(
        default=None,
        metadata={
            "name": "StaffDiscountAdult",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    staff_discount_child: Optional[str] = field(
        default=None,
        metadata={
            "name": "StaffDiscountChild",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    staff_discount_family: Optional[str] = field(
        default=None,
        metadata={
            "name": "StaffDiscountFamily",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    staff_discount_group: Optional[str] = field(
        default=None,
        metadata={
            "name": "StaffDiscountGroup",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    promotion_rail_cards: Optional[PromotionRailCardListStructure] = field(
        default=None,
        metadata={
            "name": "PromotionRailCards",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class ProductPricesStructure:
    product_type: List[ProductTypeStructure] = field(
        default_factory=list,
        metadata={
            "name": "ProductType",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "min_occurs": 1,
        },
    )


@dataclass
class PromotionFlowsStructure:
    exceptions: Optional[ExceptionsStructure] = field(
        default=None,
        metadata={
            "name": "Exceptions",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    flows: Optional[FlowsStructure] = field(
        default=None,
        metadata={
            "name": "Flows",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    exceptions_and_flows: Optional[str] = field(
        default=None,
        metadata={
            "name": "ExceptionsAndFlows",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class PromotionStructure:
    """
    :ivar change_history: Who changed the data most recently.
    :ivar promotion_identifier: Unique Identifier of the promotion
        within the knowledge base.
    :ivar type_value: Types of promotions.
    :ivar nearest_station: The name of the Promotion.
    :ivar interchange_stations: PlusBus interchange stations.
    :ivar promotion_name: The name of the Promotion.
    :ivar summary: The summary of the Promotion.
    :ivar offer_details: Details of the Promotion. Who is eligible and
        other further conditions.
    :ivar validity_period: Period during which tickets bought under the
        promotion may be used. Optional as this field is never used for
        PlusBus, expected for other types.
    :ivar validity_day_and_time: Period during which the promotion is
        valid in terms of days and time.
    :ivar available_from_date: Date from which the promotion is
        available for purchase by public.  May be earlier than the
        validity period. Optional as field is never used for PlusBus,
        expected for other types.
    :ivar region: Region within which the promotion applies.
    :ivar area_map: Link to a map showing where the promotion applies.
    :ivar timetable_links: Timetable links which only apply to plusbus.
    :ivar lead_toc: The lead toc who created the promotion or allocated
        by an admin. Can be empty if the admin does not assign one.
    :ivar applicable_tocs: List of TOCs for which promotion is
        applicable.
    :ivar operators: PlusBus Operators
    :ivar excluded_services: PlusBus Excluded Services
    :ivar product_prices:
    :ivar applicable_origin_station_groups: List of station groups for
        the origins.
    :ivar applicable_origins: List of station CRS codes at which journey
        must start.
    :ivar applicable_destination_station_groups: List of station groups
        for the destinations.
    :ivar applicable_destinations: List of station CRS codes at which
        journey must end.
    :ivar applicable_zone_of_station_groups: List of station groups for
        the zones.
    :ivar applicable_zone_of_stations: Zone containing station CRS codes
        at which offer applies for use of promotion.
    :ivar reversible: Is promotion valid travelling in both directions?
    :ivar promotion_flows: What are the flows and exceptions for this
        promotion
    :ivar further_information:
    :ivar ticket_validity_conditions: Text description of conditions.
    :ivar booking_conditions: Booking conditions that apply to the
        promotion.
    :ivar purchase_details: How and where to purchase the promotion.
    :ivar passengers: How and where to purchase the promotion.
    :ivar promotion_rail_cards: Qualifies which RailCards are applicable
        to this promotion.
    :ivar promotion_code: Three or four character code identifying an
        ordinary promotion.
    :ivar nlc_code:
    :ivar toc_contact: Information about contact at TOC.
    :ivar internal_info: Internal information about the promotion (not
        visible to public).
    :ivar ticket_name:
    :ivar adult_fares: Adult fares available under the promotion.
    :ivar child_fares: Child fares available under the promotion.
    :ivar family_fares: Family fares available under the promotion.
    :ivar concession_fares: Concession fares available under the
        promotion.
    :ivar group_fares: Group fares available under the promotion.
    :ivar day_ticket: PlusBus day ticket details.
    :ivar season_ticket: PlusBus season ticket details.
    :ivar viewable_by: Who can view the promotion.
    :ivar discounts_available:
    """

    change_history: Optional[ChangeHistoryStructure] = field(
        default=None,
        metadata={
            "name": "ChangeHistory",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
        },
    )
    promotion_identifier: Optional[str] = field(
        default=None,
        metadata={
            "name": "PromotionIdentifier",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
            "pattern": r"[A-Za-z0-9]{1,32}",
        },
    )
    type_value: Optional[str] = field(
        default=None,
        metadata={
            "name": "Type",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
        },
    )
    nearest_station: Optional[NearestStationStructure] = field(
        default=None,
        metadata={
            "name": "NearestStation",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    interchange_stations: Optional[str] = field(
        default=None,
        metadata={
            "name": "InterchangeStations",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    promotion_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "PromotionName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
            "min_length": 1,
        },
    )
    summary: Optional[str] = field(
        default=None,
        metadata={
            "name": "Summary",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
            "min_length": 1,
        },
    )
    offer_details: Optional[LinkAndDetailsStructure] = field(
        default=None,
        metadata={
            "name": "OfferDetails",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    validity_period: Optional[HalfOpenDateRangeStructure] = field(
        default=None,
        metadata={
            "name": "ValidityPeriod",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    validity_day_and_time: Optional[OpeningHoursStructure] = field(
        default=None,
        metadata={
            "name": "ValidityDayAndTime",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    available_from_date: Optional[HalfOpenDateRangeStructure] = field(
        default=None,
        metadata={
            "name": "AvailableFromDate",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    region: List[BbcRegionEnumeration] = field(
        default_factory=list,
        metadata={
            "name": "Region",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    area_map: Optional[LinkAndDetailsStructure] = field(
        default=None,
        metadata={
            "name": "AreaMap",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    timetable_links: Optional[LinkStructure] = field(
        default=None,
        metadata={
            "name": "TimetableLinks",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    lead_toc: Optional[str] = field(
        default=None,
        metadata={
            "name": "LeadToc",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "pattern": r"[A-Z]{1}[A-Z0-9]{1}",
        },
    )
    applicable_tocs: Optional[PromoApplicableTocsStructure] = field(
        default=None,
        metadata={
            "name": "ApplicableTocs",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
        },
    )
    operators: Optional[str] = field(
        default=None,
        metadata={
            "name": "Operators",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    excluded_services: Optional[str] = field(
        default=None,
        metadata={
            "name": "ExcludedServices",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    product_prices: Optional[ProductPricesStructure] = field(
        default=None,
        metadata={
            "name": "ProductPrices",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    applicable_origin_station_groups: Optional[StationGroupListStructure] = (
        field(
            default=None,
            metadata={
                "name": "ApplicableOriginStationGroups",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/promotion",
            },
        )
    )
    applicable_origins: Optional[StationListStructure] = field(
        default=None,
        metadata={
            "name": "ApplicableOrigins",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    applicable_destination_station_groups: Optional[
        StationGroupListStructure
    ] = field(
        default=None,
        metadata={
            "name": "ApplicableDestinationStationGroups",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    applicable_destinations: Optional[StationListStructure] = field(
        default=None,
        metadata={
            "name": "ApplicableDestinations",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    applicable_zone_of_station_groups: Optional[StationGroupListStructure] = (
        field(
            default=None,
            metadata={
                "name": "ApplicableZoneOfStationGroups",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/promotion",
            },
        )
    )
    applicable_zone_of_stations: Optional[StationListStructure] = field(
        default=None,
        metadata={
            "name": "ApplicableZoneOfStations",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    reversible: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Reversible",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
        },
    )
    promotion_flows: Optional[PromotionFlowsStructure] = field(
        default=None,
        metadata={
            "name": "PromotionFlows",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    further_information: Optional[LinkAndDetailsStructure] = field(
        default=None,
        metadata={
            "name": "FurtherInformation",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    ticket_validity_conditions: Optional[LinkAndDetailsStructure] = field(
        default=None,
        metadata={
            "name": "TicketValidityConditions",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    booking_conditions: Optional[LinkAndDetailsStructure] = field(
        default=None,
        metadata={
            "name": "BookingConditions",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    purchase_details: Optional[LinkAndDetailsStructure] = field(
        default=None,
        metadata={
            "name": "PurchaseDetails",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    passengers: Optional[PassengerStructure] = field(
        default=None,
        metadata={
            "name": "Passengers",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    promotion_rail_cards: Optional[PromotionRailCardListStructure] = field(
        default=None,
        metadata={
            "name": "PromotionRailCards",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    promotion_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "PromotionCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "pattern": r"[A-Z0-9]{3,4}",
        },
    )
    nlc_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "NlcCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    toc_contact: Optional[ContactDetailsStructure] = field(
        default=None,
        metadata={
            "name": "TocContact",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    internal_info: Optional[InternalInfoStructure] = field(
        default=None,
        metadata={
            "name": "InternalInfo",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    ticket_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "TicketName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    adult_fares: Optional[PromotionFareDetailsStructure] = field(
        default=None,
        metadata={
            "name": "AdultFares",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    child_fares: Optional[PromotionFareDetailsStructure] = field(
        default=None,
        metadata={
            "name": "ChildFares",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    family_fares: Optional[PromotionFareDetailsStructure] = field(
        default=None,
        metadata={
            "name": "FamilyFares",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    concession_fares: Optional[PromotionFareDetailsStructure] = field(
        default=None,
        metadata={
            "name": "ConcessionFares",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    group_fares: Optional[PromotionFareDetailsStructure] = field(
        default=None,
        metadata={
            "name": "GroupFares",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    day_ticket: Optional[DayTicketStructure] = field(
        default=None,
        metadata={
            "name": "DayTicket",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    season_ticket: Optional[SeasonTicketStructure] = field(
        default=None,
        metadata={
            "name": "SeasonTicket",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )
    viewable_by: Optional[ViewableByEnumeration] = field(
        default=None,
        metadata={
            "name": "ViewableBy",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
            "required": True,
        },
    )
    discounts_available: Optional[DiscountsAvailableStructure] = field(
        default=None,
        metadata={
            "name": "DiscountsAvailable",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/promotion",
        },
    )


@dataclass
class Promotion(PromotionStructure):
    """
    Details of a Promotion as required for the NRE Knowledge Base.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/promotion"


@dataclass
class PromotionList:
    """
    A list of promotions.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/promotion"

    promotion: List[Promotion] = field(
        default_factory=list,
        metadata={
            "name": "Promotion",
            "type": "Element",
        },
    )
