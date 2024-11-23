from dataclasses import dataclass, field
from typing import List, Optional

from xsdata.models.datatype import XmlDate

from main.rsp.gen.nre_common_v5_0 import (
    AnnotationContent,
    ChangeHistoryStructure,
    ContactDetailsStructure,
    ServiceStructure,
)

__NAMESPACE__ = "http://nationalrail.co.uk/xml/toc"


@dataclass
class OperatingPeriodStructure:
    """
    :ivar start_date: If omitted then the TOC can  never be live.
    :ivar end_date: If omitted then the TOC once live remains so
        indefinitely.
    """

    start_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "StartDate",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    end_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "EndDate",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )


@dataclass
class SupportAndInformationStructure:
    """
    :ivar customer_service: Information about customer services.
    :ivar lost_property: Information about lost property  for the TOC's
        servcies and stations.
    :ivar assisted_travel: Information for disabled passengers.
    :ivar cycle_policy_url: A link to a cycling policy documentation.
    """

    customer_service: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "CustomerService",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    lost_property: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "LostProperty",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    assisted_travel: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "AssistedTravel",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    cycle_policy_url: Optional[str] = field(
        default=None,
        metadata={
            "name": "CyclePolicyUrl",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )


@dataclass
class TicketingAndFaresStructure:
    """
    :ivar tele_sales: Information about buying tickets by phone, post or
        online.
    :ivar group_travel: Information about group tickets.
    :ivar business_travel: Information about business travel.
    :ivar seat_reservations: Information about support for seat
        reservations.
    :ivar penalty_fares_url: A link to a penalty fares details.
    :ivar buying_tickets: Whether the TOC allows tickets to be bought on
        the trains. (This is an internal only field)
    """

    tele_sales: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "TeleSales",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    group_travel: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "GroupTravel",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    business_travel: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "BusinessTravel",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    seat_reservations: Optional[ServiceStructure] = field(
        default=None,
        metadata={
            "name": "SeatReservations",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    penalty_fares_url: Optional[str] = field(
        default=None,
        metadata={
            "name": "PenaltyFaresUrl",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    buying_tickets: Optional[AnnotationContent] = field(
        default=None,
        metadata={
            "name": "BuyingTickets",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )


@dataclass
class TrainOperatingCompanyStructure:
    """
    :ivar change_history: Who changed the data most recently.
    :ivar atoc_code: Two character ATOC code identifying the company.
    :ivar atoc_member: Whether the TOC is a member of ATOC. Default is
        true.
    :ivar station_operator: Whether the TOC is a station operator.
        Default is true.
    :ivar name: The brand name of the TOC.
    :ivar legal_name: The legal company name of the TOC.
    :ivar managing_director:
    :ivar logo: A link to the TOC logo as a GIF or JPEG.
    :ivar network_map: A link to a map of the TOC's network as a PDF or
        other graphic format.
    :ivar operating_period: The dates between which the TOC is
        operational, i.e visible to the public
    :ivar head_office_contact_details: Contact details for the TOC head
        office.
    :ivar company_website: The public website address for the TOC
    :ivar support_and_information: Information about customer support
        services.
    :ivar ticketing_and_fares: Information about buying tickets and fare
        types.
    """

    change_history: Optional[ChangeHistoryStructure] = field(
        default=None,
        metadata={
            "name": "ChangeHistory",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
            "required": True,
        },
    )
    atoc_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "AtocCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
            "required": True,
            "pattern": r"[A-Z]{1}[A-Z0-9]{1}",
        },
    )
    atoc_member: Optional[bool] = field(
        default=None,
        metadata={
            "name": "AtocMember",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    station_operator: Optional[bool] = field(
        default=None,
        metadata={
            "name": "StationOperator",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    name: Optional[str] = field(
        default=None,
        metadata={
            "name": "Name",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
            "required": True,
        },
    )
    legal_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "LegalName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
            "required": True,
        },
    )
    managing_director: Optional[str] = field(
        default=None,
        metadata={
            "name": "ManagingDirector",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    logo: Optional[str] = field(
        default=None,
        metadata={
            "name": "Logo",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    network_map: Optional[str] = field(
        default=None,
        metadata={
            "name": "NetworkMap",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    operating_period: Optional[OperatingPeriodStructure] = field(
        default=None,
        metadata={
            "name": "OperatingPeriod",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    head_office_contact_details: Optional[ContactDetailsStructure] = field(
        default=None,
        metadata={
            "name": "HeadOfficeContactDetails",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    company_website: Optional[str] = field(
        default=None,
        metadata={
            "name": "CompanyWebsite",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    support_and_information: Optional[SupportAndInformationStructure] = field(
        default=None,
        metadata={
            "name": "SupportAndInformation",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )
    ticketing_and_fares: Optional[TicketingAndFaresStructure] = field(
        default=None,
        metadata={
            "name": "TicketingAndFares",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/toc",
        },
    )


@dataclass
class TrainOperatingCompany(TrainOperatingCompanyStructure):
    """
    Details of a Train Operating Company as required for the NRE Knowledge Base.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/toc"


@dataclass
class TrainOperatingCompanyList:
    """
    A list of Train Operating Companies.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/toc"

    train_operating_company: List[TrainOperatingCompany] = field(
        default_factory=list,
        metadata={
            "name": "TrainOperatingCompany",
            "type": "Element",
        },
    )
