import base64
import dataclasses
import traceback
import typing
import datetime
import Crypto.Hash.TupleHash128
import hashlib

import binascii
from django.utils import timezone
from . import models, vdv, uic, rsp, templatetags, apn, gwallet, sncf, elb, ssb, ssb1, email


class TicketError(Exception):
    def __init__(self, title, message, exception=None):
        self.title = title
        self.message = message
        self.exception = exception


@dataclasses.dataclass
class VDVTicket:
    root_ca: vdv.CertificateData
    issuing_ca: vdv.CertificateData
    envelope_certificate: vdv.CertificateData
    raw_ticket: bytes
    ticket: vdv.VDVTicket

    @property
    def ticket_type(self) -> str:
        return "VDV"

    def type(self) -> str:
        if self.ticket.product_number in (
                9999,  # Deutschlandticket subscription
                9998,  # Deutschlandjobticket subscription
                9997,  # Startkarte Deutschlandticket
                9996,  # Semesterticket Deutschlandticket Upgrade subscription
                9995,  # Semesterdeutschlandticket subscription
        ):
            return models.Ticket.TYPE_DEUTCHLANDTICKET
        else:
            return models.Ticket.TYPE_UNKNOWN

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        ticket_type = self.type()
        if ticket_type == models.Ticket.TYPE_DEUTCHLANDTICKET:
            passenger_data = next(filter(lambda d: isinstance(d, vdv.ticket.PassengerData), self.ticket.product_data),
                                  None)
            if passenger_data:
                hd.update(b"deutschlandticket")
                hd.update(self.ticket.product_org_id.to_bytes(8, "big"))
                hd.update(passenger_data.forename.encode("utf-8"))
                hd.update(passenger_data.surname.encode("utf-8"))
                hd.update(str(passenger_data.date_of_birth).encode("utf-8"))
                return base64.b32hexencode(hd.digest()).decode("utf-8")

        hd.update(b"unknown-vdv")
        hd.update(self.ticket.ticket_id.to_bytes(8, "big"))
        hd.update(self.ticket.ticket_org_id.to_bytes(8, "big"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class UICTicket:
    raw_bytes: bytes
    envelope: uic.Envelope
    head: uic.HeadV1
    layout: typing.Optional[uic.LayoutV1]
    flex: typing.Optional[uic.Flex]
    dt_ti: typing.Optional[uic.dt.DTRecordTI]
    dt_pa: typing.Optional[uic.dt.DTRecordPA]
    db_bl: typing.Optional[uic.db.DBRecordBL]
    cd_ut: typing.Optional[uic.cd.CDRecordUT]
    oebb_99: typing.Optional[uic.oebb.OeBBRecord99]
    db_vu: typing.Optional[uic.db_vu.DBRecordVU]
    vor_fi: typing.Optional[uic.vor.VORRecordFI]
    vor_vd: typing.Optional[uic.vor.VORRecordVD]
    other_records: typing.List[uic.envelope.Record]

    @property
    def ticket_type(self) -> str:
        return "UIC"

    def type(self) -> str:
        if self.flex:
            security_num = self.flex.data["issuingDetail"].get("securityProviderNum")
            issuer_num = self.flex.data["issuingDetail"].get("issuerNum")
            issuer_name = self.flex.data["issuingDetail"].get("issuerName")
            if len(self.flex.data.get("transportDocument", [])) >= 1:
                ticket_type, ticket = self.flex.data["transportDocument"][0]["ticket"]
                if ticket_type == "openTicket":
                    if len(self.flex.data.get("travelerDetail", {}).get("traveler", [])) >= 1 and \
                            ((issuer_num or security_num) in (
                                    1080,  # Deutsche Bahn
                                    5143,  # AMCON Software GmbH
                                    5173,  # Nahverkehrsservice Sachsen-Anhalt
                                    3076,  # Transdev GmbH
                                    3497,  # Regensburger Verkehrsverbund GmbH
                                    5008,  # Verkehrsverbund Rhein-Neckar GmbH
                            ) or self.dt_ti or self.dt_pa):
                        if ticket.get("productIdNum") in (
                                9999,  # Deutschlandticket subscription
                                9998,  # Deutschlandjobticket subscription
                                9997,  # Startkarte Deutschlandticket
                                9996,  # Semesterticket Deutschlandticket Upgrade subscription
                                9995,  # Semesterdeutschlandticket subscription
                        ):
                            return models.Ticket.TYPE_DEUTCHLANDTICKET
                        else:
                            return models.Ticket.TYPE_FAHRKARTE
                    else:
                        return models.Ticket.TYPE_FAHRKARTE
                elif ticket_type == "pass":
                    if issuer_num == 9901 or security_num == 9901:
                        return models.Ticket.TYPE_INTERRAIL
                    elif issuer_name == "BMK":
                        return models.Ticket.TYPE_KLIMATICKET
                elif ticket_type == "customerCard":
                    return models.Ticket.TYPE_BAHNCARD
                elif ticket_type == "reservation":
                    return models.Ticket.TYPE_RESERVIERUNG
        elif self.db_bl:
            return models.Ticket.TYPE_FAHRKARTE
        elif self.cd_ut:
            return models.Ticket.TYPE_FAHRKARTE
        elif self.oebb_99:
            return models.Ticket.TYPE_FAHRKARTE
        elif self.dt_ti:
            if self.dt_ti.product_name == "Deutschlandticket":
                return models.Ticket.TYPE_DEUTCHLANDTICKET
            return models.Ticket.TYPE_FAHRKARTE
        elif self.layout and self.layout.standard in ("RCT2", "RTC2"):
            return models.Ticket.TYPE_FAHRKARTE

        return models.Ticket.TYPE_UNKNOWN

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        ticket_type = self.type()

        if ticket_type == models.Ticket.TYPE_DEUTCHLANDTICKET:
            if self.flex:
                passenger = self.flex.data.get("travelerDetail", {}).get("traveler", [{}])[0]
                dob_year = passenger.get("yearOfBirth", 0)
                dob_month = passenger.get("monthOfBirth", 0)
                dob_day = passenger.get("dayOfBirthInMonth", 0)
                hd.update(b"deutschlandticket")
                hd.update(self.issuing_rics().to_bytes(8, "big"))
                hd.update(passenger.get("firstName").encode("utf-8"))
                hd.update(passenger.get("lastName").encode("utf-8"))
                hd.update(f"{dob_year:04d}-{dob_month:02d}-{dob_day:02d}".encode("utf-8"))
                return base64.b32hexencode(hd.digest()).decode("utf-8")
            elif self.dt_pa:
                hd.update(b"deutschlandticket")
                hd.update(self.issuing_rics().to_bytes(8, "big"))
                hd.update(self.dt_pa.passenger_name.encode("utf-8"))
                return base64.b32hexencode(hd.digest()).decode("utf-8")

        elif ticket_type == models.Ticket.TYPE_BAHNCARD:
            card = self.flex.data["transportDocument"][0]["ticket"][1]
            hd.update(b"bahncard")
            hd.update(self.flex.data["issuingDetail"].get("issuerNum", 0).to_bytes(8, "big"))
            if "cardIdIA5" in card:
                hd.update(card["cardIdIA5"].encode("utf-8"))
            else:
                hd.update(str(card.get("cardIdNum", 0)).encode("utf-8"))
            return base64.b32hexencode(hd.digest()).decode("utf-8")

        elif ticket_type == models.Ticket.TYPE_FAHRKARTE:
            hd.update(b"fahrkarte")
            if self.flex:
                ticket = self.flex.data["transportDocument"][0]["ticket"][1]
                hd.update(self.flex.data["issuingDetail"].get("issuerNum", 0).to_bytes(8, "big"))
                if "referenceIA5" in ticket:
                    hd.update(ticket["referenceIA5"].encode("utf-8"))
                elif "referenceNum" in ticket:
                    hd.update(str(ticket["referenceNum"]).encode("utf-8"))
                else:
                    hd.update(self.ticket_id().encode("utf-8"))
            else:
                hd.update(self.issuing_rics().to_bytes(8, "big"))
                hd.update(self.ticket_id().encode("utf-8"))
            return base64.b32hexencode(hd.digest()).decode("utf-8")

        elif ticket_type == models.Ticket.TYPE_RESERVIERUNG:
            ticket = self.flex.data["transportDocument"][0]["ticket"][1]
            hd.update(b"reservierung")
            hd.update(self.flex.data["issuingDetail"].get("issuerNum", 0).to_bytes(8, "big"))
            if "referenceIA5" in ticket:
                hd.update(ticket["referenceIA5"].encode("utf-8"))
            elif "referenceNum" in ticket:
                hd.update(str(ticket["referenceNum"]).encode("utf-8"))
            else:
                hd.update(self.ticket_id().encode("utf-8"))
            return base64.b32hexencode(hd.digest()).decode("utf-8")

        elif ticket_type == models.Ticket.TYPE_INTERRAIL:
            interrail_pass = self.flex.data["transportDocument"][0]["ticket"][1]
            hd.update(b"interrail")
            if "referenceIA5" in interrail_pass:
                hd.update(interrail_pass["referenceIA5"].encode("utf-8"))
            elif "referenceNum" in interrail_pass:
                hd.update(str(interrail_pass["referenceNum"]).encode("utf-8"))
            else:
                hd.update(self.ticket_id().encode("utf-8"))
            return base64.b32hexencode(hd.digest()).decode("utf-8")

        elif ticket_type == models.Ticket.TYPE_KLIMATICKET:
            klimaticket_pass = self.flex.data["transportDocument"][0]["ticket"][1]
            hd.update(b"klimaticket")
            if "referenceIA5" in klimaticket_pass:
                hd.update(klimaticket_pass["referenceIA5"].encode("utf-8"))
            elif "referenceNum" in klimaticket_pass:
                hd.update(str(klimaticket_pass["referenceNum"]).encode("utf-8"))
            else:
                hd.update(self.ticket_id().encode("utf-8"))
            return base64.b32hexencode(hd.digest()).decode("utf-8")

        else:
            hd.update(b"unknown-uic")
            hd.update(self.issuing_rics().to_bytes(4, "big"))
            hd.update(self.ticket_id().encode("utf-8"))
            return base64.b32encode(hd.digest()).decode("utf-8")

    def issuing_rics(self) -> int:
        if self.head and self.head.distributing_rics:
            return self.head.distributing_rics

        if self.flex:
            if r := self.flex.issuing_rics():
                return r

        return self.envelope.issuer_rics

    def distributor(self):
        return uic.rics.get_rics(self.issuing_rics())

    def ticket_id(self) -> str:
        if self.head:
            return self.head.ticket_id
        elif self.flex:
            return self.flex.ticket_id()
        else:
            return ""

    def issuing_time(self) -> typing.Optional[datetime.datetime]:
        if self.head:
            return self.head.issuing_time.as_datetime()
        elif self.flex:
            return self.flex.issuing_time()
        else:
            return None

    def specimen(self) -> bool:
        if self.head:
            return self.head.flags.specimen
        elif self.flex:
            return self.flex.specimen()
        else:
            return False

    @classmethod
    def from_envelope(cls, ticket_bytes: bytes, ticket_envelope: uic.Envelope,
                      context: vdv.ticket.Context) -> "UICTicket":
        return cls(
            raw_bytes=ticket_bytes,
            envelope=ticket_envelope,
            head=parse_ticket_uic_head(ticket_envelope),
            layout=parse_ticket_uic_layout(ticket_envelope),
            flex=parse_ticket_uic_flex(ticket_envelope),
            dt_ti=parse_ticket_uic_dt_ti(ticket_envelope),
            dt_pa=parse_ticket_uic_dt_pa(ticket_envelope),
            db_bl=parse_ticket_uic_db_bl(ticket_envelope),
            db_vu=parse_ticket_uic_db_vu(ticket_envelope, context),
            cd_ut=parse_ticket_uic_cd_ut(ticket_envelope),
            oebb_99=parse_ticket_uic_oebb_99(ticket_envelope),
            vor_fi=parse_ticket_uic_vor_fi(ticket_envelope),
            vor_vd=parse_ticket_uic_vor_vd(ticket_envelope),
            other_records=[r for r in ticket_envelope.records if not (
                    r.id.startswith("U_") or r.id == "0080BL" or r.id == "0080VU"
                    or r.id == "1154UT" or r.id == "118199"
                    or r.id == "5197TI" or r.id == "5197PA"
                    or r.id == "5008TI" or r.id == "5008PA"
                    or r.id == "3497TI" or r.id == "3497PA"
                    or r.id == "5245TI" or r.id == "5245PA"
                    or r.id == "3565TI" or r.id == "3565PA"
                    or r.id == "3306FI" or r.id == "3306VD" or r.id == "3606AA"
            )]
        )


@dataclasses.dataclass
class RSPTicket:
    rsp_type: str
    issuer_id: str
    ticket_ref: str
    raw_ticket: bytes
    data: typing.Union[rsp.RailcardData, rsp.TicketData]

    @property
    def ticket_type(self) -> str:
        return "RSP"

    def type(self) -> str:
        if self.rsp_type == "08":
            return models.Ticket.TYPE_RAILCARD
        elif self.rsp_type == "06":
            return models.Ticket.TYPE_FAHRKARTE
        else:
            return models.Ticket.TYPE_UNKNOWN

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        if self.rsp_type == "08":
            hd.update(b"rsp-railcard")
            hd.update(self.data.railcard_number.encode("utf-8"))
            return base64.b32encode(hd.digest()).decode("utf-8")

        hd.update(b"rsp")
        hd.update(self.rsp_type.encode("utf-8"))
        hd.update(self.issuer_id.encode("utf-8"))
        hd.update(self.ticket_ref.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")

    @property
    def rsp_type_name(self):
        if self.rsp_type == "08":
            return "Railcard"
        elif self.rsp_type == "06":
            return "Ticket"
        else:
            return "Unknown"

    @property
    def raw_ticket_hex(self):
        return ":".join(f"{b:02x}" for b in self.raw_ticket)

    def issuer_name(self):
        return rsp.issuers.issuer_name(self.issuer_id)


@dataclasses.dataclass
class SNCFTicket:
    raw_ticket: bytes
    data: sncf.SNCFTicket

    @property
    def ticket_type(self) -> str:
        return "SNCF"

    def type(self) -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"sncf")
        hd.update(self.data.ticket_number.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class ELBTicket:
    raw_ticket: bytes
    data: elb.ELBTicket

    @property
    def ticket_type(self) -> str:
        return "ELB"

    def type(self) -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"elb")
        hd.update(self.data.pnr.encode("utf-8"))
        hd.update(self.data.sequence_number.to_bytes(2, "big"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class SSBTicket:
    raw_ticket: bytes
    envelope: ssb.Envelope
    data: typing.Union[
        ssb.NonReservationTicket, ssb.IntegratedReservationTicket,
        ssb.GroupTicket, ssb.ns_keycard.Keycard,
        ssb.sz.Ticket
    ]

    @property
    def ticket_type(self) -> str:
        return "SSB"

    def type(self) -> str:
        if isinstance(self.data, ssb.NonReservationTicket):
            return models.Ticket.TYPE_FAHRKARTE
        elif isinstance(self.data, ssb.IntegratedReservationTicket):
            return models.Ticket.TYPE_RESERVIERUNG
        elif isinstance(self.data, ssb.GroupTicket):
            return models.Ticket.TYPE_FAHRKARTE
        elif isinstance(self.data, ssb.ns_keycard.Keycard):
            return models.Ticket.TYPE_KEYCARD
        elif isinstance(self.data, ssb.sz.Ticket):
            return models.Ticket.TYPE_FAHRKARTE
        else:
            return models.Ticket.TYPE_UNKNOWN

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"ssb")
        hd.update(self.envelope.issuer_rics.to_bytes(8, "big"))
        hd.update(self.envelope.ticket_type.to_bytes(8, "big"))
        hd.update(self.data.pnr.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class SSB1Ticket:
    raw_ticket: bytes
    ticket: ssb1.Ticket

    @property
    def ticket_type(self) -> str:
        return "SSB1"

    def type(self) -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"ssb1")
        hd.update(self.ticket.issuer_rics.to_bytes(8, "big"))
        hd.update(self.ticket.pnr.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")


def parse_ticket_vdv(ticket_bytes: bytes, context: vdv.ticket.Context) -> VDVTicket:
    pki_store = vdv.CertificateStore()
    try:
        pki_store.load_certificates()
    except vdv.util.VDVException:
        raise TicketError(
            title="Internal error",
            message="The PKI certificates could not be loaded. This is almost certainly a bug.",
            exception=traceback.format_exc()
        )

    raw_root_ca = pki_store.find_certificate(vdv.CAReference.root())
    if not raw_root_ca:
        raise TicketError(
            title="Internal error",
            message="The root CA couldn't be found. This is almost certainly a bug.",
        )

    try:
        root_ca = vdv.Certificate.parse(raw_root_ca)
    except vdv.util.VDVException:
        raise TicketError(
            title="Internal error",
            message="The root CA certificate is invalid. This is almost certainly a bug.",
            exception=traceback.format_exc()
        )

    if root_ca.needs_ca_key():
        raise TicketError(
            title="Internal error",
            message="The root CA certificate is encrypted and requires a CA key. This is almost certainly a bug."
        )

    try:
        root_ca_data = vdv.CertificateData.parse(root_ca)
    except vdv.util.VDVException:
        raise TicketError(
            title="Internal error",
            message="The root CA certificate data is invalid. This is almost certainly a bug.",
            exception=traceback.format_exc()
        )

    if root_ca_data.ca_reference != vdv.CAReference.root() or \
            root_ca_data.certificate_holder_reference != vdv.CAReference.root():
        raise TicketError(
            title="Internal error",
            message="The root CA appears to not be a root. This is almost certainly a bug."
        )

    try:
        root_ca.verify_signature(root_ca_data)
    except vdv.util.VDVException:
        raise TicketError(
            title="Internal error",
            message="The root CA certificate signature is invalid. This is almost certainly a bug.",
            exception=traceback.format_exc()
        )

    try:
        envelope = vdv.EnvelopeV2.parse(ticket_bytes)
    except vdv.util.VDVException:
        raise TicketError(
            title="This doesn't look like a valid VDV ticket",
            message="You may have scanned something that is not a VDV ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    raw_issuing_ca = pki_store.find_certificate(envelope.ca_reference)
    if not raw_issuing_ca:
        raise TicketError(
            title="Unknown issuing certificate",
            message="The certificate that issued this ticket is not known - the ticket is likely invalid."
        )

    try:
        issuing_ca = vdv.Certificate.parse(raw_issuing_ca)
    except vdv.util.VDVException:
        raise TicketError(
            title="Invalid issuing certificate",
            message="The issuing CA can't be decoded - this is likely a bug.",
            exception=traceback.format_exc()
        )

    if issuing_ca.needs_ca_key():
        try:
            issuing_ca.decrypt_with_ca_key(root_ca_data)
        except vdv.util.VDVException:
            raise TicketError(
                title="Unable to decrypt issuing certificate",
                message="The issuing CA is encrypted and can't be decrypted - the ticket is likely invalid.",
                exception=traceback.format_exc()
            )
    else:
        try:
            issuing_ca.verify_signature(root_ca_data)
        except vdv.util.VDVException:
            raise TicketError(
                title="Invalid issuing certificate signature",
                message="The issuing CA has an invalid signature - the ticket is likely invalid.",
                exception=traceback.format_exc()
            )

    try:
        issuing_ca_data = vdv.CertificateData.parse(issuing_ca)
    except vdv.util.VDVException:
        raise TicketError(
            title="Invalid issuing certificate data",
            message="The issuing CA couldn't be decoded - this is likely a bug.",
            exception=traceback.format_exc()
        )

    if issuing_ca_data.ca_reference != root_ca_data.certificate_holder_reference:
        raise TicketError(
            title="Broken certificate chain",
            message="The issuing CA isn't issued by the root CA - the ticket is likely invalid."
        )

    if envelope.ca_reference != issuing_ca_data.certificate_holder_reference:
        raise TicketError(
            title="Broken certificate chain",
            message="The ticket certificate isn't issued by the issuing CA - the ticket is likely invalid."
        )

    if envelope.certificate.needs_ca_key():
        try:
            envelope.certificate.decrypt_with_ca_key(issuing_ca_data)
        except vdv.util.VDVException:
            raise TicketError(
                title="Unable to decrypt ticket certificate",
                message="The ticket certificate is encrypted and can't be decrypted - the ticket is likely invalid.",
                exception=traceback.format_exc()
            )
    else:
        try:
            envelope.certificate.verify_signature(issuing_ca_data)
        except vdv.util.VDVException:
            raise TicketError(
                title="Invalid ticket certificate signature",
                message="The ticket certificate has an invalid signature - the ticket is likely invalid.",
                exception=traceback.format_exc()
            )

    try:
        envelope_certificate_data = vdv.CertificateData.parse(envelope.certificate)
    except vdv.util.VDVException:
        raise TicketError(
            title="Invalid ticket certificate data",
            message="The ticket certificate couldn't be decoded - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )

    try:
        ticket_data = envelope.decrypt_with_cert(envelope_certificate_data)
    except vdv.util.VDVException:
        raise TicketError(
            title="Unable to decrypt ticket",
            message="The ticket data couldn't be decrypted - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )

    try:
        ticket = vdv.VDVTicket.parse(ticket_data, context)
    except vdv.util.VDVException:
        raise TicketError(
            title="Unable to parse ticket",
            message="The ticket data is invalid - this is likely a bug.",
            exception=traceback.format_exc()
        )

    return VDVTicket(
        root_ca=root_ca_data,
        issuing_ca=issuing_ca_data,
        envelope_certificate=envelope_certificate_data,
        raw_ticket=ticket_data,
        ticket=ticket
    )


def parse_ticket_uic_head(ticket_envelope: uic.Envelope) -> typing.Optional[uic.HeadV1]:
    head_record = next(filter(lambda r: r.id == "U_HEAD", ticket_envelope.records), None)
    if not head_record:
        return None

    if head_record.version != 1:
        raise TicketError(
            title="Unsupported header record version",
            message=f"The header record version {head_record.version} is not supported."
        )

    try:
        return uic.HeadV1.parse(head_record.data)
    except uic.util.UICException:
        raise TicketError(
            title="Invalid header record",
            message="The header record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_layout(ticket_envelope: uic.Envelope) -> typing.Optional[uic.LayoutV1]:
    layout_record = next(filter(lambda r: r.id in ("U_TLAY", "3606AA"), ticket_envelope.records), None)
    if not layout_record:
        return None

    if layout_record.version != 1:
        raise TicketError(
            title="Unsupported layout record version",
            message=f"The layout record version {layout_record.version} is not supported."
        )

    try:
        return uic.LayoutV1.parse(layout_record.data, ticket_envelope.issuer_rics, layout_record.is_utf8_len)
    except uic.util.UICException:
        raise TicketError(
            title="Invalid layout record",
            message="The layout record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_flex(ticket_envelope: uic.Envelope) -> typing.Optional[uic.Flex]:
    flex_record = next(filter(lambda r: r.id == "U_FLEX", ticket_envelope.records), None)
    if not flex_record:
        return None

    try:
        return uic.Flex.parse(flex_record.version, flex_record.data)
    except uic.util.UICException:
        raise TicketError(
            title="Invalid flexible data record",
            message="The flexible record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_dt_ti(ticket_envelope: uic.Envelope) -> typing.Optional[uic.dt.DTRecordTI]:
    ti_record = next(filter(
        lambda r: (
                          r.id == "5197TI" or r.id == "5008TI" or r.id == "3497TI" or r.id == "5245TI" or
                          r.id == "3565TI"
                  ) and r.version == 1,
        ticket_envelope.records
    ), None)
    if not ti_record:
        return None

    try:
        return uic.dt.DTRecordTI.parse(ti_record.data, ti_record.version)
    except uic.dt.DTException:
        raise TicketError(
            title="Invalid TI record",
            message="The TI record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_dt_pa(ticket_envelope: uic.Envelope) -> typing.Optional[uic.dt.DTRecordTI]:
    pa_record = next(filter(
        lambda r: (
                          r.id == "5197PA" or r.id == "5008PA" or r.id == "3497PA" or r.id == "5245PA" or
                          r.id == "3565PA"
                  ) and r.version == 1,
        ticket_envelope.records
    ), None)
    if not pa_record:
        return None

    try:
        return uic.dt.DTRecordPA.parse(pa_record.data, pa_record.version)
    except uic.dt.DTException:
        raise TicketError(
            title="Invalid PA record",
            message="The PA record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_db_bl(ticket_envelope: uic.Envelope) -> typing.Optional[uic.db.DBRecordBL]:
    bl_record = next(filter(lambda r: r.id == "0080BL", ticket_envelope.records), None)
    if not bl_record:
        return None

    try:
        return uic.db.DBRecordBL.parse(bl_record.data, bl_record.version)
    except uic.db.DBException:
        raise TicketError(
            title="Invalid DB BL record",
            message="The DB BL record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_cd_ut(ticket_envelope: uic.Envelope) -> typing.Optional[uic.cd.CDRecordUT]:
    ut_record = next(filter(lambda r: r.id == "1154UT" and r.version == 1, ticket_envelope.records), None)
    if not ut_record:
        return None

    try:
        return uic.cd.CDRecordUT.parse(ut_record.data, ut_record.version)
    except uic.cd.CDException:
        raise TicketError(
            title="Invalid CD UT record",
            message="The CD UT record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_db_vu(ticket_envelope: uic.Envelope, context: vdv.ticket.Context) -> typing.Optional[
    uic.db_vu.DBRecordVU]:
    vu_record = next(filter(lambda r: r.id == "0080VU" and r.version == 1, ticket_envelope.records), None)
    if not vu_record:
        return None

    try:
        return uic.db_vu.DBRecordVU.parse(vu_record.data, vu_record.version, context)
    except uic.db_vu.DBVUException:
        raise TicketError(
            title="Invalid DB VU Record",
            message="The DB VU record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_oebb_99(ticket_envelope: uic.Envelope) -> typing.Optional[uic.oebb.OeBBRecord99]:
    oebb_record = next(filter(lambda r: r.id == "118199" and r.version == 1, ticket_envelope.records), None)
    if not oebb_record:
        return None

    try:
        return uic.oebb.OeBBRecord99.parse(oebb_record.data, oebb_record.version)
    except uic.oebb.OeBBException:
        raise TicketError(
            title="Invalid OeBB 99 record",
            message="The OeBB 99 record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_vor_fi(ticket_envelope: uic.Envelope) -> typing.Optional[uic.vor.VORRecordFI]:
    vor_record = next(filter(lambda r: r.id == "3306FI" and r.version == 1, ticket_envelope.records), None)
    if not vor_record:
        return None

    try:
        return uic.vor.VORRecordFI.parse(vor_record.data, vor_record.version)
    except uic.vor.VORRecordFI:
        raise TicketError(
            title="Invalid VOR FI record",
            message="The VOR FI record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_vor_vd(ticket_envelope: uic.Envelope) -> typing.Optional[uic.vor.VORRecordVD]:
    vor_record = next(filter(lambda r: r.id == "3306VD" and r.version == 1, ticket_envelope.records), None)
    if not vor_record:
        return None

    try:
        return uic.vor.VORRecordVD.parse(vor_record.data, vor_record.version)
    except uic.vor.VORException:
        raise TicketError(
            title="Invalid VOR VD record",
            message="The VOR VD record is invalid - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic(ticket_bytes: bytes, context: vdv.ticket.Context) -> UICTicket:
    try:
        ticket_envelope = uic.Envelope.parse(ticket_bytes)
    except uic.util.UICException:
        raise TicketError(
            title="This doesn't look like a valid UIC ticket",
            message="You may have scanned something that is not a UIC ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    return UICTicket.from_envelope(ticket_bytes, ticket_envelope, context)


def parse_ticket_rsp(ticket_bytes: bytes) -> RSPTicket:
    pki_store = rsp.CertificateStore()
    pki_store.load_certificates()

    try:
        ticket_envelope = rsp.Envelope.parse(ticket_bytes)
    except rsp.RSPException:
        raise TicketError(
            title="This doesn't look like a valid RSP ticket",
            message="You may have scanned something that is not a RSP ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    if ticket_envelope.issuer_id not in pki_store.certificates:
        raise TicketError(
            title="Unknown RSP issuer",
            message=f"We don't have any keys for the RSP issuer {ticket_envelope.issuer_id} - we can't decode this ticket",
        )

    ticket_payload = None
    for cert in pki_store.certificates[ticket_envelope.issuer_id]:
        try:
            ticket_payload = ticket_envelope.decrypt_with_cert(cert)
        except rsp.RSPException:
            raise TicketError(
                title="Unable to decrypt RSP ticket",
                message="Its likely the signature over this ticket has been forged - the ticket is invalid.",
                exception=traceback.format_exc()
            )
        if ticket_payload:
            break

    if not ticket_payload:
        raise TicketError(
            title="Unable to decrypt RSP ticket",
            message="None of the issuer's public keys match the RSP ticket",
        )

    if ticket_envelope.ticket_type == "08":
        data = rsp.RailcardData.parse(ticket_payload)
    elif ticket_envelope.ticket_type == "06":
        try:
            data = rsp.TicketData.parse(ticket_payload)
        except rsp.RSPException:
            raise TicketError(
                title="This doesn't look like a valid RSP ticket",
                message="You may have scanned something that is not a RSP ticket, the ticket is corrupted, or there "
                        "is a bug in this program.",
                exception=traceback.format_exc()
            )
    else:
        raise TicketError(
            title="Unsupported RSP ticket type",
            message=f"We don't know how to parse type {ticket_envelope.ticket_type} tickets",
        )

    return RSPTicket(
        rsp_type=ticket_envelope.ticket_type,
        ticket_ref=ticket_envelope.ticket_ref,
        issuer_id=ticket_envelope.issuer_id,
        raw_ticket=ticket_payload,
        data=data
    )


def parse_ticket_sncf(ticket_bytes: bytes) -> SNCFTicket:
    try:
        data = sncf.SNCFTicket.parse(ticket_bytes)
    except sncf.SNCFException:
        raise TicketError(
            title="This doesn't look like a valid SNCF ticket",
            message="You may have scanned something that is not an SNCF ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    return SNCFTicket(
        raw_ticket=ticket_bytes,
        data=data
    )


def parse_ticket_elb(ticket_bytes: bytes) -> ELBTicket:
    try:
        data = elb.ELBTicket.parse(ticket_bytes)
    except elb.ELBException:
        raise TicketError(
            title="This doesn't look like a valid ELB ticket",
            message="You may have scanned something that is not an ELB ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    return ELBTicket(
        raw_ticket=ticket_bytes,
        data=data
    )


def parse_ticket_ssb(ticket_bytes: bytes) -> SSBTicket:
    try:
        envelope = ssb.Envelope.parse(ticket_bytes)
    except ssb.SSBException:
        raise TicketError(
            title="This doesn't look like a valid SSB ticket",
            message="You may have scanned something that is not an SSB ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    if envelope.ticket_type == 1:
        data = ssb.IntegratedReservationTicket.parse(envelope.data, envelope.issuer_rics)
    elif envelope.ticket_type == 2:
        data = ssb.NonReservationTicket.parse(envelope.data, envelope.issuer_rics)
    elif envelope.ticket_type == 3:
        data = ssb.GroupTicket.parse(envelope.data, envelope.issuer_rics)
    elif envelope.ticket_type == 4:
        data = ssb.Pass.parse(envelope.data)
    elif envelope.issuer_rics == 1184 and envelope.ticket_type == 21:
        data = ssb.ns_keycard.Keycard.parse(envelope.data)
    elif envelope.issuer_rics == 1179 and envelope.ticket_type == 21:
        data = ssb.sz.Ticket.parse(envelope.data)
    else:
        raise TicketError(
            title="Unsupported SSB ticket type",
            message=f"We don't know how to parse type {envelope.ticket_type} SSB tickets from {envelope.issuer_rics}",
        )

    return SSBTicket(
        raw_ticket=ticket_bytes,
        envelope=envelope,
        data=data
    )

def parse_ticket_ssb1(ticket_bytes: bytes) -> SSB1Ticket:
    try:
        ticket = ssb1.Ticket.parse(ticket_bytes)
    except ssb1.SSB1Exception:
        raise TicketError(
            title="This doesn't look like a valid SSB ticket",
            message="You may have scanned something that is not an SSB ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    return SSB1Ticket(
        raw_ticket=ticket_bytes,
        ticket=ticket
    )


def parse_ticket(ticket_bytes: bytes, account: typing.Optional["models.Account"]) -> \
        typing.Union[VDVTicket, UICTicket, RSPTicket, SNCFTicket, ELBTicket, SSBTicket, SSB1Ticket]:
    context = vdv.ticket.Context(
        account_forename=account.user.first_name if account else None,
        account_surname=account.user.last_name if account else None,
    )
    if len(ticket_bytes) == 114 and (ticket_bytes[0] & 0xF0) >> 4 == 3:
        return parse_ticket_ssb(ticket_bytes)

    try:
        d = base64.b64decode(ticket_bytes)
        if (d[0] & 0xF0) >> 4 in (2, 3):
            return parse_ticket_ssb(d)
    except binascii.Error as e:
        pass

    if len(ticket_bytes) == 107 and (ticket_bytes[0] & 0xF0) >> 4 in (1, 2):
        return parse_ticket_ssb1(ticket_bytes)

    if ticket_bytes[:4] == b"i0CV":
        return parse_ticket_sncf(ticket_bytes)

    if ticket_bytes[:3] == b"#UT":
        return parse_ticket_uic(ticket_bytes, context)

    if ticket_bytes[:2] in (b"06", b"08"):
        return parse_ticket_rsp(ticket_bytes)

    if ticket_bytes[:1] == b"e":
        return parse_ticket_elb(ticket_bytes)

    return parse_ticket_vdv(ticket_bytes, context)


def to_dict_json(elements: typing.List[typing.Tuple[str, typing.Any]]) -> dict:
    def encode_value(v):
        if isinstance(v, bytes) or isinstance(v, bytearray):
            return base64.b64encode(v).decode("ascii")
        else:
            return v

    return {k: encode_value(v) for k, v in elements}


def create_ticket_obj(
        ticket_obj: "models.Ticket",
        ticket_bytes: bytes,
        ticket_data: typing.Union[VDVTicket, UICTicket, RSPTicket, SNCFTicket, ELBTicket, SSBTicket, SSB1Ticket],
) -> bool:
    created = False
    barcode_hash = hashlib.sha256(ticket_bytes).hexdigest()

    if isinstance(ticket_data, VDVTicket):
        _, created = models.VDVTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "ticket_org_id": ticket_data.ticket.ticket_org_id,
                "validity_start": ticket_data.ticket.validity_start.as_datetime(),
                "validity_end": ticket_data.ticket.validity_end.as_datetime(),
                "barcode_data": ticket_bytes,
                "decoded_data": {
                    "root_ca": dataclasses.asdict(ticket_data.root_ca, dict_factory=to_dict_json),
                    "issuing_ca": dataclasses.asdict(ticket_data.issuing_ca, dict_factory=to_dict_json),
                    "envelope_certificate":
                        dataclasses.asdict(ticket_data.envelope_certificate, dict_factory=to_dict_json),
                    "ticket": base64.b64encode(ticket_data.raw_ticket).decode("ascii"),
                }
            }
        )
    elif isinstance(ticket_data, UICTicket):
        if ticket_data.db_vu:
            data = bytearray()
            for e in ticket_data.envelope.records:
                if e.id != "0080VU":
                    data.extend(e.data)
            barcode_hash = hashlib.sha256(data).hexdigest()
        else:
            barcode_hash = hashlib.sha256(ticket_data.envelope.signed_data).hexdigest()

        validity_start = None
        validity_end = None
        if ticket_data.flex:
            docs = ticket_data.flex.data.get("transportDocument")
            if docs:
                if docs[0]["ticket"][0] in ("openTicket", "pass"):
                    validity_start = templatetags.rics.rics_valid_from(docs[0]["ticket"][1], ticket_data.issuing_time())
                    validity_end = templatetags.rics.rics_valid_until(docs[0]["ticket"][1], ticket_data.issuing_time())
                elif docs[0]["ticket"][0] == "customerCard":
                    validity_start = templatetags.rics.rics_valid_from_date(docs[0]["ticket"][1])
                    validity_end = templatetags.rics.rics_valid_until_date(docs[0]["ticket"][1])

        _, created = models.UICTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "distributor_rics": ticket_data.issuing_rics(),
                "issuing_time": ticket_data.issuing_time(),
                "barcode_data": ticket_bytes,
                "validity_start": validity_start,
                "validity_end": validity_end,
                "decoded_data": {
                    "envelope": dataclasses.asdict(ticket_data.envelope, dict_factory=to_dict_json),
                }
            }
        )
    elif isinstance(ticket_data, RSPTicket):
        validity_start = None
        validity_end = None
        if isinstance(ticket_data.data, rsp.RailcardData):
            validity_start = ticket_data.data.validity_start_time()
            validity_end = ticket_data.data.validity_end_time()

        _, created = models.RSPTicketInstance.objects.update_or_create(
            ticket_type=ticket_data.rsp_type,
            issuer_id=ticket_data.issuer_id,
            reference=ticket_data.ticket_ref,
            defaults={
                "ticket": ticket_obj,
                "barcode_data": ticket_bytes,
                "validity_start": validity_start,
                "validity_end": validity_end,
                "decoded_data": {
                    "raw_ticket": base64.b64encode(ticket_data.raw_ticket).decode("ascii"),
                }
            }
        )
    elif isinstance(ticket_data, SNCFTicket):
        _, created = models.SNCFTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "barcode_data": ticket_bytes,
            }
        )
    elif isinstance(ticket_data, ELBTicket):
        _, created = models.ELBTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "barcode_data": ticket_bytes,
            }
        )
    elif isinstance(ticket_data, SSBTicket):
        _, created = models.SSBTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "distributor_rics": ticket_data.envelope.issuer_rics,
                "barcode_data": ticket_bytes,
                "ssb_data": ticket_data.raw_ticket,
            }
        )
    elif isinstance(ticket_data, SSB1Ticket):
        _, created = models.SSB1TicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "distributor_rics": ticket_data.ticket.issuer_rics,
                "barcode_data": ticket_bytes,
            }
        )
    return created


def update_from_subscription_barcode(barcode_data: bytes,
                                     account: typing.Optional["models.Account"]) -> "models.Ticket":
    decoded_ticket = parse_ticket(barcode_data, account=account)

    should_update = False
    created = False
    ticket_pk = decoded_ticket.pk()
    ticket_obj = models.Ticket.objects.filter(pk=ticket_pk).first()
    if not ticket_obj:
        should_update = True
        created = True
        ticket_obj = models.Ticket.objects.create(
            pk=ticket_pk,
            last_updated=timezone.now(),
        )

    ticket_obj.ticket_type = decoded_ticket.type()
    ticket_obj.account = account
    if create_ticket_obj(ticket_obj, barcode_data, decoded_ticket):
        should_update = True

    if should_update:
        ticket_obj.last_updated = timezone.now()

    ticket_obj.save()

    if should_update:
        apn.notify_ticket(ticket_obj)
        gwallet.sync_ticket(ticket_obj)

    if created:
        email.send_new_ticket_email(ticket_obj)

    return ticket_obj
