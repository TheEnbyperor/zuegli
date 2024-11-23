from dataclasses import dataclass, field
from typing import List, Optional

from xsdata.models.datatype import XmlDateTime

from main.rsp.gen.nre_common_v5_0 import (
    ChangeHistoryStructure,
    HalfOpenTimestampRangeStructure,
)

__NAMESPACE__ = "http://nationalrail.co.uk/xml/incident"


@dataclass
class AffectedOperatorStructure:
    """
    Type for Annotated reference to affected  Operator.

    :ivar operator_ref: Identifier of Operator.
    :ivar operator_name: Public Name of Operator. Can be derived from
        OperatorRef.
    """

    operator_ref: Optional[str] = field(
        default=None,
        metadata={
            "name": "OperatorRef",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "required": True,
            "pattern": r"[A-Z]{1}[A-Z0-9]{1}",
        },
    )
    operator_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "OperatorName",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "min_length": 1,
        },
    )


@dataclass
class InfoLinkStructure:
    """
    Type for a general hyperlink.

    :ivar uri: URI for link.
    :ivar label: Label for Link
    """

    uri: Optional[str] = field(
        default=None,
        metadata={
            "name": "Uri",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "required": True,
        },
    )
    label: Optional[str] = field(
        default=None,
        metadata={
            "name": "Label",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "min_length": 1,
        },
    )


@dataclass
class SourceStructure:
    """
    Type for a source ie provider of information.

    :ivar twitter_hashtag: Twitter hash tag for the source.
    """

    twitter_hashtag: Optional[str] = field(
        default=None,
        metadata={
            "name": "TwitterHashtag",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )


@dataclass
class AffectsStructure:
    """
    Type for Location model for scope of incident or effect.

    :ivar operators: Operators affected by incident.
    :ivar routes_affected:
    """

    operators: Optional["AffectsStructure.Operators"] = field(
        default=None,
        metadata={
            "name": "Operators",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )
    routes_affected: Optional[str] = field(
        default=None,
        metadata={
            "name": "RoutesAffected",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )

    @dataclass
    class Operators:
        """
        :ivar affected_operator: Operators of services affected by
            incident.
        """

        affected_operator: List[AffectedOperatorStructure] = field(
            default_factory=list,
            metadata={
                "name": "AffectedOperator",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/incident",
                "min_occurs": 1,
            },
        )


@dataclass
class PtIncidentStructure:
    """
    Type for individual Incident.

    :ivar creation_time: Time of creation of incident
    :ivar change_history: Who changed the data most recently.
    :ivar participant_ref: Unique identifier of system issuing entry
        identifier. If absent, taken from Context element. May be
        different from that in Context, indicating that the incident is
        forwarded from another system  - without being allocated a new
        identifier by the inbtermediate system. Note that the
        ExternalCode may be used to retain the external System's
        identifier to allow round trip processing.
    :ivar incident_number: Identifier of entry. Must be unique within
        Participant's current data horizon. Monotonically increasing,
        seqience with time of issue. Normally also unique within
        Participant (ie also outside of the current horizon) so that a
        uniform namespace can also be used for archived messages as
        well.
    :ivar version: Version number if entry is update to a previous
        version. Unique within IncidentNumber. Monotonically increasing
        within IncidentNumber.  Any values for  classification,
        description, affects, effects that are present in an update
        replace any values on previous incidents and updates with the
        same identifier.  Values that are not updated remain in effect.
    :ivar source: Information about source of information, that is,
        where the agent using the capture client obtained an item of
        information, or in the case of an automated feed, an identifier
        of the specific feed.  Can be used to obtain updates, verify
        details or otherwise assess relevance.
    :ivar outer_validity_period:
    :ivar validity_period: Overall inclusive Period of applicability of
        incident
    :ivar planned: Whether the incident was planned (eg engineering
        works) or unplanned (eg service alteration). Default is false,
        i.e. unplanned.
    :ivar summary: Summary of incident. If absent should be generated
        from structure elements / and or by condensing Description.
    :ivar description: Description of incident. Should not repeat any
        strap line incldued in Summary.
    :ivar info_links: Hyperlinks to other resources associated with
        incident.
    :ivar affects: Structured model identifiying parts of transport
        network affected by incident. Operator and Network values will
        be defaulted to values in general Context unless explicitly
        overridden.
    :ivar cleared_incident:
    :ivar incident_priority:
    :ivar p0_summary:
    """

    creation_time: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "CreationTime",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "required": True,
        },
    )
    change_history: Optional[ChangeHistoryStructure] = field(
        default=None,
        metadata={
            "name": "ChangeHistory",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "required": True,
        },
    )
    participant_ref: Optional[str] = field(
        default=None,
        metadata={
            "name": "ParticipantRef",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )
    incident_number: Optional[str] = field(
        default=None,
        metadata={
            "name": "IncidentNumber",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "required": True,
            "pattern": r"[A-Za-z0-9]{32}",
        },
    )
    version: Optional[int] = field(
        default=None,
        metadata={
            "name": "Version",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )
    source: Optional[SourceStructure] = field(
        default=None,
        metadata={
            "name": "Source",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )
    outer_validity_period: Optional[HalfOpenTimestampRangeStructure] = field(
        default=None,
        metadata={
            "name": "OuterValidityPeriod",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )
    validity_period: List[HalfOpenTimestampRangeStructure] = field(
        default_factory=list,
        metadata={
            "name": "ValidityPeriod",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "min_occurs": 1,
        },
    )
    planned: bool = field(
        default=False,
        metadata={
            "name": "Planned",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "required": True,
        },
    )
    summary: Optional[str] = field(
        default=None,
        metadata={
            "name": "Summary",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "required": True,
            "min_length": 1,
        },
    )
    description: Optional[str] = field(
        default=None,
        metadata={
            "name": "Description",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
            "required": True,
            "min_length": 1,
        },
    )
    info_links: Optional["PtIncidentStructure.InfoLinks"] = field(
        default=None,
        metadata={
            "name": "InfoLinks",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )
    affects: Optional[AffectsStructure] = field(
        default=None,
        metadata={
            "name": "Affects",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )
    cleared_incident: Optional[bool] = field(
        default=None,
        metadata={
            "name": "ClearedIncident",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )
    incident_priority: Optional[int] = field(
        default=None,
        metadata={
            "name": "IncidentPriority",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )
    p0_summary: Optional[str] = field(
        default=None,
        metadata={
            "name": "P0Summary",
            "type": "Element",
            "namespace": "http://nationalrail.co.uk/xml/incident",
        },
    )

    @dataclass
    class InfoLinks:
        """
        :ivar info_link: Hyperlink description
        """

        info_link: List[InfoLinkStructure] = field(
            default_factory=list,
            metadata={
                "name": "InfoLink",
                "type": "Element",
                "namespace": "http://nationalrail.co.uk/xml/incident",
                "min_occurs": 1,
            },
        )


@dataclass
class PtIncident(PtIncidentStructure):
    """
    Details of a single incident.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/incident"


@dataclass
class Incidents:
    """
    Public Transport Incidents.
    """

    class Meta:
        namespace = "http://nationalrail.co.uk/xml/incident"

    pt_incident: List[PtIncident] = field(
        default_factory=list,
        metadata={
            "name": "PtIncident",
            "type": "Element",
        },
    )
