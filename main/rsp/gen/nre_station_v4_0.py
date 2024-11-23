from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from main.rsp.gen.nre_common_v5_0 import (
    AnnotatedStructure,
    AnnotationContent,
    AvailableFacilityStructure,
    ChangeHistoryStructure,
    CrsCodeListStructure,
    OpeningHoursStructure,
    PlatformCoverageEnumeration,
    PostalAddressStructure,
    ServiceStructure,
    TelephoneStructure,
    TravelcardsStructure,
)

__NAMESPACE__ = "http://nationalrail.co.uk/xml/station"


@dataclass
class AlternativeIdentifiersStructure:
    """
    :ivar national_location_code: NLC code for this station. This
        element is required for SID export to RJIS.
    :ivar tiplocs: A list of TIPLOCs located at this station.
    """

    national_location_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "NationalLocationCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
            "min_length": 4,
            "max_length": 7,
        },
    )
    tiplocs: Optional["AlternativeIdentifiersStructure.Tiplocs"] = field(
        default=None,
        metadata={
            "name": "Tiplocs",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )

    @dataclass
    class Tiplocs:
        """
        :ivar tiploc: Timing Point Location code. There may be more than
            one of these per station.
        """

        tiploc: List[str] = field(
            default_factory=list,
            metadata={
                "name": "Tiploc",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/station",
                "min_length": 4,
                "max_length": 7,
            },
        )


@dataclass
class Cctvstructure:
    """
    :ivar available: Whether the station has CCTV or not.
    """

    class Meta:
        name = "CCTVStructure"

    available: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Available",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
        },
    )


class Cisenumeration(Enum):
    DEPARTURE_SCREENS = "DepartureScreens"
    ARRIVAL_SCREENS = "ArrivalScreens"
    ANNOUNCEMENTS = "Announcements"


@dataclass
class ChargesStructure:
    off_peak: Optional[str] = field(
        default=None,
        metadata={
            "name": "Off-peak",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    per_hour: Optional[str] = field(
        default=None,
        metadata={
            "name": "PerHour",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    daily: Optional[str] = field(
        default=None,
        metadata={
            "name": "Daily",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    weekly: Optional[str] = field(
        default=None,
        metadata={
            "name": "Weekly",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    monthly: Optional[str] = field(
        default=None,
        metadata={
            "name": "Monthly",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    three_monthly: Optional[str] = field(
        default=None,
        metadata={
            "name": "ThreeMonthly",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    six_monthly: Optional[str] = field(
        default=None,
        metadata={
            "name": "SixMonthly",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    annual: Optional[str] = field(
        default=None,
        metadata={
            "name": "Annual",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    free: Optional[str] = field(
        default=None,
        metadata={
            "name": "Free",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class PenaltyFaresStructure:
    train_operator: List[str] = field(
        default_factory=list,
        metadata={
            "name": "TrainOperator",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    url: Optional[str] = field(
        default=None,
        metadata={
            "name": "Url",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


class StaffingLevelEnumeration(Enum):
    """
    Available levels of staffing at a station.
    """

    FULL_TIME = "fullTime"
    PART_TIME = "partTime"
    UNSTAFFED = "unstaffed"


@dataclass
class StationAlertStructure:
    """
    :ivar alert_text: A description the alerts for the station.
    """

    alert_text: Optional[str] = field(
        default=None,
        metadata={
            "name": "AlertText",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


class StepFreeAccessCoverageEnumeration(Enum):
    """
    Amount of station accessible without steps.

    :cvar WHOLE_STATION: The whole station is accessible, including all
        platforms and ticket office.
    :cvar PARTIAL_STATION: Parts of the station are accessible. Used
        when neither allPlatforms nor wholeStation are applicable.
    :cvar ALL_PLATFORMS: All platforms are accessible, but not the
        ticket office.
    :cvar NO_PART_OF_STATION: Neither the platforms nor the ticket
        office are accessible.
    :cvar UNKNOWN: Accessibility details are unknown.
    """

    WHOLE_STATION = "wholeStation"
    PARTIAL_STATION = "partialStation"
    ALL_PLATFORMS = "allPlatforms"
    NO_PART_OF_STATION = "noPartOfStation"
    UNKNOWN = "unknown"


@dataclass
class TicketMachineStructure:
    """
    :ivar available: Whether there is a Ticket Machine at this station.
    """

    available: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Available",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class TicketPickupStructure:
    ticket_office: Optional[bool] = field(
        default=None,
        metadata={
            "name": "TicketOffice",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    ticket_machine: Optional[bool] = field(
        default=None,
        metadata={
            "name": "TicketMachine",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    not_available: Optional[bool] = field(
        default=None,
        metadata={
            "name": "NotAvailable",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class TrainOperatingCompaniesStructure:
    toc_ref: List[str] = field(
        default_factory=list,
        metadata={
            "name": "TocRef",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "min_occurs": 1,
            "pattern": r"[A-Z]{1}[A-Z0-9]{1}",
        },
    )


@dataclass
class CarParkStructure(ServiceStructure):
    """
    :ivar name: Name of the car park.
    :ivar spaces: Total number of spaces available.
    :ivar charges: Description of parking charges.
    :ivar number_accessible_spaces:
    :ivar accessible_spaces_note:
    :ivar accessible_car_park_equipment:
    :ivar accessible_car_park_equipment_note:
    :ivar cctv:
    """

    name: Optional[str] = field(
        default=None,
        metadata={
            "name": "Name",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    spaces: Optional[int] = field(
        default=None,
        metadata={
            "name": "Spaces",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    charges: Optional[ChargesStructure] = field(
        default=None,
        metadata={
            "name": "Charges",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    number_accessible_spaces: Optional[int] = field(
        default=None,
        metadata={
            "name": "NumberAccessibleSpaces",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    accessible_spaces_note: Optional[str] = field(
        default=None,
        metadata={
            "name": "AccessibleSpacesNote",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    accessible_car_park_equipment: Optional[bool] = field(
        default=None,
        metadata={
            "name": "AccessibleCarParkEquipment",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    accessible_car_park_equipment_note: Optional[str] = field(
        default=None,
        metadata={
            "name": "AccessibleCarParkEquipmentNote",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    cctv: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Cctv",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class CycleStorageStructure:
    """
    :ivar spaces: Number of spaces available
    :ivar sheltered: Degree of shelter for the Cycle Storage area
    :ivar cctv: If the Cycle Storage area is completely covered by CCTV
        coverage
    :ivar location: The location in the station of the Cycle Storage
    :ivar annotation: Any additional information related to Cycle
        Storage
    :ivar type_value: Type of Cycle Storage Available
    """

    spaces: Optional[int] = field(
        default=None,
        metadata={
            "name": "Spaces",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    sheltered: Optional[PlatformCoverageEnumeration] = field(
        default=None,
        metadata={
            "name": "Sheltered",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    cctv: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Cctv",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    location: Optional[AnnotationContent] = field(
        default=None,
        metadata={
            "name": "Location",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    annotation: Optional[AnnotationContent] = field(
        default=None,
        metadata={
            "name": "Annotation",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    type_value: List[str] = field(
        default_factory=list,
        metadata={
            "name": "Type",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class FaresStructure:
    """
    :ivar ticket_office: Ticket Office for the station.
    :ivar prepurchase_collection: Whether pre-purchased tickets can be
        collected at this station.
    :ivar ticket_machine: Details on the Ticket Machine facilities at
        the station
    :ivar oystercard_issued: Whether you can use Oyster/Pre-Pay at this
        station.
    :ivar oystercard_topup: Whether you can Top Up Oyster cards at this
        station.
    :ivar use_oystercard: Validate Oyster cards at the station.
    :ivar oyster_comments: Oyster card related comments.
    :ivar always_show_oyster_card_fields: Always show the oyster card
        fields.
    :ivar smartcard_issued: Can a smartcard be issued at the station.
    :ivar smartcard_topup: Whether you can Top Up Smartcards at the
        station.
    :ivar smartcard_validator: Validate Smartcards at the station.
    :ivar smartcard_comments: Smartcard related comments.
    :ivar travelcard: Travelcard information for this station.
    :ivar penalty_fares: Information of penalty fares at this station.
    """

    ticket_office: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "TicketOffice",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    prepurchase_collection: Optional[TicketPickupStructure] = field(
        default=None,
        metadata={
            "name": "PrepurchaseCollection",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    ticket_machine: Optional[TicketMachineStructure] = field(
        default=None,
        metadata={
            "name": "TicketMachine",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    oystercard_issued: Optional[bool] = field(
        default=None,
        metadata={
            "name": "OystercardIssued",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    oystercard_topup: Optional[TicketPickupStructure] = field(
        default=None,
        metadata={
            "name": "OystercardTopup",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    use_oystercard: Optional[bool] = field(
        default=None,
        metadata={
            "name": "UseOystercard",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    oyster_comments: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "OysterComments",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    always_show_oyster_card_fields: Optional[bool] = field(
        default=None,
        metadata={
            "name": "AlwaysShowOysterCardFields",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    smartcard_issued: Optional[bool] = field(
        default=None,
        metadata={
            "name": "SmartcardIssued",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    smartcard_topup: Optional[TicketPickupStructure] = field(
        default=None,
        metadata={
            "name": "SmartcardTopup",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    smartcard_validator: Optional[bool] = field(
        default=None,
        metadata={
            "name": "SmartcardValidator",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    smartcard_comments: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "SmartcardComments",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    travelcard: Optional[TravelcardsStructure] = field(
        default=None,
        metadata={
            "name": "Travelcard",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    penalty_fares: Optional[PenaltyFaresStructure] = field(
        default=None,
        metadata={
            "name": "PenaltyFares",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class InformationSystemsStructure:
    """
    :ivar information_available_from_staff: Facilities available for the
        Customer Information System.
    :ivar information_services_open: Facilities available for the
        Customer Information System.
    :ivar cis: Facilities available for the Customer Information System.
    :ivar customer_help_points: Is there an information point / desk /
        kiosk?
    """

    information_available_from_staff: List[str] = field(
        default_factory=list,
        metadata={
            "name": "InformationAvailableFromStaff",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    information_services_open: Optional[OpeningHoursStructure] = field(
        default=None,
        metadata={
            "name": "InformationServicesOpen",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    cis: List[Cisenumeration] = field(
        default_factory=list,
        metadata={
            "name": "CIS",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    customer_help_points: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "CustomerHelpPoints",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class PassengerServicesStructure:
    """
    :ivar customer_service: Customer service contact details for the
        station.
    :ivar tele_sales: Contact details for buying tickets for travel from
        this station.
    :ivar left_luggage: Information about any left luggage facilities at
        the station.
    :ivar lost_property: Contact details for lost property enquiries at
        the station.
    """

    customer_service: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "CustomerService",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    tele_sales: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "TeleSales",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    left_luggage: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "LeftLuggage",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    lost_property: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "LostProperty",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class RailReplacementStructure(AnnotatedStructure):
    """
    :ivar rail_replacement_map: Link to a map showing the station in the
        local area.
    """

    rail_replacement_map: List[str] = field(
        default_factory=list,
        metadata={
            "name": "RailReplacementMap",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class StaffingStructure:
    """
    :ivar staffing_level: Whether the station is staffed
    :ivar closed_circuit_television: Is there CCTV in operation at the
        station?
    """

    staffing_level: Optional[StaffingLevelEnumeration] = field(
        default=None,
        metadata={
            "name": "StaffingLevel",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    closed_circuit_television: Optional[Cctvstructure] = field(
        default=None,
        metadata={
            "name": "ClosedCircuitTelevision",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
        },
    )


@dataclass
class StepFreeAccessStructure(AnnotatedStructure):
    """
    Details of step free access to the station.

    :ivar coverage: Indicates how much of the station is accessible.
        Further details should be given in the annotation.
    """

    coverage: Optional[StepFreeAccessCoverageEnumeration] = field(
        default=None,
        metadata={
            "name": "Coverage",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class ToiletsStructure:
    """
    :ivar available: A boolean value indicating whether toliets are
        available
    :ivar location: A boolean value indicating whether toliets are
        available
    """

    available: Optional[bool] = field(
        default=None,
        metadata={
            "name": "Available",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    location: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "Location",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class AccessibilityStructure:
    """
    :ivar helpline: Impaired access helpline for station.
    :ivar staff_help_available: Are there staff available to help
        customers with impaired access? Defaults to unknown.
    :ivar induction_loop: Is there an Induction Loop for Deaf people at
        the station? Defaults to unknown.
    :ivar accessible_ticket_machines: Are Ticket Machines Accessible to
        all Disabled people?
    :ivar height_adjusted_ticket_office_counter: Has the booking office
        got a low-level/split level counter?
    :ivar ramp_for_train_access: Is there a ramp for train access
        available at the station?
    :ivar accessible_taxis: Are accessible taxis available
    :ivar accessible_public_telephones: Are there low-level/text phones
        available?
    :ivar nearest_stations_with_more_facilities: List of recommended
        nearby stations with more impaired access facilities. Specified
        by CRS code.
    :ivar national_key_toilets: Is there an Impaired Access toilet run
        as part of the National Key Scheme at the station? Defaults to
        unknown.
    :ivar step_free_access: Information on step free access to the
        station.
    :ivar ticket_gates: Are ticket gates available at the station.
    :ivar impaired_mobility_set_down: Is there an Impaired Mobility set
        down point at or near to the entrance to the station? Defaults
        to unknown.
    :ivar wheelchairs_available: Are there wheelchairs available at the
        station?
    """

    helpline: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "Helpline",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    staff_help_available: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "StaffHelpAvailable",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    induction_loop: Optional[bool] = field(
        default=None,
        metadata={
            "name": "InductionLoop",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    accessible_ticket_machines: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "AccessibleTicketMachines",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    height_adjusted_ticket_office_counter: Optional[
        AvailableFacilityStructure
    ] = field(
        default=None,
        metadata={
            "name": "HeightAdjustedTicketOfficeCounter",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    ramp_for_train_access: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "RampForTrainAccess",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    accessible_taxis: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "AccessibleTaxis",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    accessible_public_telephones: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "AccessiblePublicTelephones",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    nearest_stations_with_more_facilities: Optional[CrsCodeListStructure] = (
        field(
            default=None,
            metadata={
                "name": "NearestStationsWithMoreFacilities",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/station",
            },
        )
    )
    national_key_toilets: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "NationalKeyToilets",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    step_free_access: Optional[StepFreeAccessStructure] = field(
        default=None,
        metadata={
            "name": "StepFreeAccess",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    ticket_gates: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "TicketGates",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    impaired_mobility_set_down: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "ImpairedMobilitySetDown",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    wheelchairs_available: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "WheelchairsAvailable",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class InterchangeStructure:
    """
    :ivar cycle_storage: Availability of Cycle Storage facilities
    :ivar car_park: Car park availability and information. Defaults to
        unknown.
    :ivar rail_replacement_services: Information on Rail Replacement
        Services
    :ivar taxi_rank: Is there a taxi rank at the station? Defaults to
        unknown. Annotation can provide TrainTaxi url.
    :ivar onward_travel:
    :ivar metro_services: The metro services available from this
        station.
    :ivar airport: Does the Station give access to an Airport?
    :ivar port: Does the Station give access to an Port or ferry
        service?
    :ivar car_hire: Can cars be hired at or near the station? Defaults
        to unknown.
    :ivar cycle_hire: Can cycles be hired at or near the station?
        Defaults to unknown.
    """

    cycle_storage: Optional[CycleStorageStructure] = field(
        default=None,
        metadata={
            "name": "CycleStorage",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
        },
    )
    car_park: List[CarParkStructure] = field(
        default_factory=list,
        metadata={
            "name": "CarPark",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    rail_replacement_services: Optional[RailReplacementStructure] = field(
        default=None,
        metadata={
            "name": "RailReplacementServices",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    taxi_rank: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "TaxiRank",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    onward_travel: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "OnwardTravel",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    metro_services: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "MetroServices",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    airport: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "Airport",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    port: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "Port",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    car_hire: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "CarHire",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    cycle_hire: Optional[AnnotatedStructure] = field(
        default=None,
        metadata={
            "name": "CycleHire",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class StationFacilitiesStructure(AnnotatedStructure):
    """
    :ivar first_class_lounge: Does the station have a first class
        lounge? Defaults to unavailable.
    :ivar seated_area: Does the station have an area with seats?
        Defaults to unknown.
    :ivar waiting_room: Does the station have a general waiting room?
        Defaults to unknown.
    :ivar trolleys: Are luggage trolleys available at the station for
        passenger use? Defaults to unknown.
    :ivar station_buffet: Does the station have a Buffet? Defaults to
        unknown.
    :ivar toilets: Details on station toilets
    :ivar baby_change: Does the station have facilities to change
        babies's nappies? Defaults to unknown.
    :ivar showers: Does the station have showers? Defaults to unknown.
    :ivar telephones: Details the stations telephone facilities
    :ivar wi_fi: Does the station have a public 802.11 wireless network?
        Defaults to unknown.
    :ivar web_kiosk: Does the station have a Kiosk? Defaults to unknown.
    :ivar post_box: Does the station have a post box? Defaults to
        unknown.
    :ivar tourist_information: Defaults to unknown.
    :ivar atm_machine: Does the station have an ATM Machine? Defaults to
        unknown.
    :ivar bureau_de_change: Does the station have a Bureau de Change?
        Defaults to unknown.
    :ivar shops: Does the station have shops? Defaults to unknown.
    """

    first_class_lounge: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "FirstClassLounge",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    seated_area: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "SeatedArea",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    waiting_room: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "WaitingRoom",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    trolleys: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "Trolleys",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    station_buffet: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "StationBuffet",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    toilets: Optional[ToiletsStructure] = field(
        default=None,
        metadata={
            "name": "Toilets",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    baby_change: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "BabyChange",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    showers: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "Showers",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    telephones: Optional[TelephoneStructure] = field(
        default=None,
        metadata={
            "name": "Telephones",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    wi_fi: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "WiFi",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    web_kiosk: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "WebKiosk",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    post_box: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "PostBox",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    tourist_information: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "TouristInformation",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    atm_machine: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "AtmMachine",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    bureau_de_change: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "BureauDeChange",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    shops: Optional[AvailableFacilityStructure] = field(
        default=None,
        metadata={
            "name": "Shops",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class StationStructure:
    """
    Information about an individual station.

    :ivar change_history: Who changed the data  most recently.
    :ivar crs_code: Three character CRS code identifying a station.
    :ivar alternative_identifiers: Alternative identifiers for this
        station. Note that these are NOT to be used as a primary key for
        this station.
    :ivar name: The canonical name of the station. This is the full name
        of the station and must be unique.
    :ivar sixteen_character_name: A unique name for the station with
        maximum 16 characters. This element is required for SID export
        to RJIS, and is output even if the canonical name is shorter
        than 16 characters.
    :ivar address: Address of  the station based on apd standard
        apd:UKAddressStructure 5 line address and postcode .
    :ivar longitude: The longitude of the station as supplied by NaPTAN.
    :ivar latitude: The longitude of the station as supplied by NaPTAN.
    :ivar station_operator: The operator of the station: a TOC or
        Network Rail.
    :ivar staffing: Information about the staffing of the station.
    :ivar information_systems: Details fo the passenger information
        available at the station.
    :ivar fares: Fare related information.
    :ivar passenger_services: Contact information and opening hours of
        services offered at this station.
    :ivar station_facilities: Availability of facilities at this
        station.
    :ivar accessibility: Availability of facilities at this station.
    :ivar interchange: Information about changing between services at
        the station.
    :ivar station_alerts: Alerts affecting the station.
    :ivar train_operating_companies:
    :ivar station_category:
    """

    change_history: Optional[ChangeHistoryStructure] = field(
        default=None,
        metadata={
            "name": "ChangeHistory",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
        },
    )
    crs_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "CrsCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
            "length": 3,
            "pattern": r"[A-Z]{3}",
        },
    )
    alternative_identifiers: Optional[AlternativeIdentifiersStructure] = field(
        default=None,
        metadata={
            "name": "AlternativeIdentifiers",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
        },
    )
    name: Optional[str] = field(
        default=None,
        metadata={
            "name": "Name",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
        },
    )
    sixteen_character_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "SixteenCharacterName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
            "max_length": 16,
        },
    )
    address: Optional[PostalAddressStructure] = field(
        default=None,
        metadata={
            "name": "Address",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    longitude: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "Longitude",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
        },
    )
    latitude: Optional[Decimal] = field(
        default=None,
        metadata={
            "name": "Latitude",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
        },
    )
    station_operator: Optional[str] = field(
        default=None,
        metadata={
            "name": "StationOperator",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
            "pattern": r"[A-Z]{1}[A-Z0-9]{1}",
        },
    )
    staffing: Optional[StaffingStructure] = field(
        default=None,
        metadata={
            "name": "Staffing",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
            "required": True,
        },
    )
    information_systems: Optional[InformationSystemsStructure] = field(
        default=None,
        metadata={
            "name": "InformationSystems",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    fares: Optional[FaresStructure] = field(
        default=None,
        metadata={
            "name": "Fares",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    passenger_services: Optional[PassengerServicesStructure] = field(
        default=None,
        metadata={
            "name": "PassengerServices",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    station_facilities: Optional[StationFacilitiesStructure] = field(
        default=None,
        metadata={
            "name": "StationFacilities",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    accessibility: Optional[AccessibilityStructure] = field(
        default=None,
        metadata={
            "name": "Accessibility",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    interchange: Optional[InterchangeStructure] = field(
        default=None,
        metadata={
            "name": "Interchange",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    station_alerts: Optional[StationAlertStructure] = field(
        default=None,
        metadata={
            "name": "StationAlerts",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )
    train_operating_companies: Optional[TrainOperatingCompaniesStructure] = (
        field(
            default=None,
            metadata={
                "name": "TrainOperatingCompanies",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/station",
                "required": True,
            },
        )
    )
    station_category: Optional[str] = field(
        default=None,
        metadata={
            "name": "StationCategory",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/station",
        },
    )


@dataclass
class Station(StationStructure):
    """
    Describes a station's services and facilities.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/station"


@dataclass
class StationList:
    """
    A list of stations.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/station"

    station: List[Station] = field(
        default_factory=list,
        metadata={
            "name": "Station",
            "type": "Element",
        },
    )
