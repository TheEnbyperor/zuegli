from dataclasses import dataclass, field
from typing import List, Optional

__NAMESPACE__ = "http://nationalrail.co.uk/xml/serviceindicator"


@dataclass
class NsiserviceGroupStructure:
    class Meta:
        name = "NSIServiceGroupStructure"

    group_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "GroupName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )
    current_disruption: Optional[str] = field(
        default=None,
        metadata={
            "name": "CurrentDisruption",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
            "pattern": r"[A-Za-z0-9]{1,32}",
        },
    )
    custom_detail: Optional[str] = field(
        default=None,
        metadata={
            "name": "CustomDetail",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )
    custom_url: Optional[str] = field(
        default=None,
        metadata={
            "name": "CustomURL",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )


@dataclass
class NationalServiceIndicatorStructure:
    toc_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "TocCode",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
            "required": True,
            "pattern": r"[A-Z]{1}[A-Z0-9]{1}",
        },
    )
    toc_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "TocName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
            "required": True,
        },
    )
    status: Optional[str] = field(
        default=None,
        metadata={
            "name": "Status",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
            "required": True,
        },
    )
    status_image: Optional[str] = field(
        default=None,
        metadata={
            "name": "StatusImage",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )
    status_description: Optional[str] = field(
        default=None,
        metadata={
            "name": "StatusDescription",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )
    service_group: List[NsiserviceGroupStructure] = field(
        default_factory=list,
        metadata={
            "name": "ServiceGroup",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )
    twitter_account: Optional[str] = field(
        default=None,
        metadata={
            "name": "TwitterAccount",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )
    additional_info: Optional[str] = field(
        default=None,
        metadata={
            "name": "AdditionalInfo",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )
    custom_additional_info: Optional[str] = field(
        default=None,
        metadata={
            "name": "CustomAdditionalInfo",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )


@dataclass
class NationalServiceIndicatorListStructure:
    toc: List[NationalServiceIndicatorStructure] = field(
        default_factory=list,
        metadata={
            "name": "TOC",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/serviceindicator",
        },
    )


@dataclass
class Nsi(NationalServiceIndicatorListStructure):
    class Meta:
        name = "NSI"
        namespace = "http://nationalrail.co.uk/xml/serviceindicator"
