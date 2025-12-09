import base64
import base45
import dataclasses
import traceback
import typing
import datetime
import Crypto.Hash.TupleHash128
import hashlib
import enum
import binascii
import ber_tlv.tlv
import math
import re
from django.utils import timezone
from . import models, vdv, uic, rsp, templatetags, apn, gwallet, sncf, elb, ssb, ssb1, email, hzpp, swisspass, iata, \
    bahnbonus, flexi_ticket, ts2, sncb_train_plus, adif, mav

def base_encode(data: bytes, alphabet: str) -> str:
    number = int.from_bytes(data, byteorder="big")
    output = ""
    while number != 0:
        number, i = divmod(number, len(alphabet))
        output = f"{alphabet[i]}{output}"
    return output

def base_decode(data: str, alphabet: str) -> bytes:
    output_len = int(math.ceil((len(data) * math.log2(len(alphabet))) / 8))
    number = 0
    for char in data:
        if char not in alphabet:
            raise ValueError("Invalid character")
        i = alphabet.index(char)
        number *= len(alphabet)
        number += i
    return number.to_bytes(output_len, byteorder="big")


UIC_URL_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ$:*+-."
UIC_URL_RE = re.compile(r"^(?:https|HTTPS):\/\/[a-zA-Z0-9.-]+\/.*\$UIC:([0-9A-Z$:*+-.]+)$")


class TicketError(Exception):
    def __init__(self, title, message, exception=None):
        self.title = title
        self.message = message
        self.exception = exception


@dataclasses.dataclass
class TicketContext:
    forename: typing.Optional[str]
    surname: typing.Optional[str]
    email: typing.Optional[str]


@dataclasses.dataclass
class TicketContexts:
    contexts: typing.List[TicketContext]


@dataclasses.dataclass
class VDVTicket:
    root_ca: "vdv.CertificateData"
    issuing_ca: "vdv.CertificateData"
    envelope_certificate: "vdv.CertificateData"
    raw_ticket: bytes
    ticket: "vdv.VDVTicket"
    motics: typing.Optional["vdv.Motics"]

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
            return models.Ticket.TYPE_FAHRKARTE

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

    def revoked_status(self) -> typing.Optional[str]:
        blocklist_entry = models.VDVBlocklistItem.objects.filter(
            item_type=models.VDVBlocklistItem.ITEM_BERECHTIGUNG,
            org_id=self.ticket.ticket_org_id,
            item_id=self.ticket.ticket_id,
        ).order_by("-instance_counter").first()
        if blocklist_entry:
            return blocklist_entry.get_lock_mode_display()
        return None


@dataclasses.dataclass
class UICTicket:
    raw_bytes: bytes
    envelope: typing.Optional["uic.Envelope"] = None
    head: typing.Optional["uic.HeadV1"] = None
    dosipas_envelope: typing.Optional["uic.DOSIPASEnvelope"] = None
    layout: typing.Optional["uic.LayoutV1"] = None
    flex: typing.Optional["uic.Flex"] = None
    dosipas_dcd: typing.Optional["uic.dosipas.DCD"] = None
    dt_ti: typing.Optional["uic.dt.DTRecordTI"] = None
    dt_pa: typing.Optional["uic.dt.DTRecordPA"] = None
    db_bl: typing.Optional["uic.db.DBRecordBL"] = None
    cd_ut: typing.Optional["uic.cd.CDRecordUT"] = None
    oebb_99: typing.Optional["uic.oebb.OeBBRecord99"] = None
    db_vu: typing.Optional["uic.db_vu.DBRecordVU"] = None
    vor_fi: typing.Optional["uic.vor.VORRecordFI"] = None
    vor_vd: typing.Optional["uic.vor.VORRecordVD"] = None
    vor_fk: typing.Optional["uic.vor.VORRecordFK"] = None
    st01: typing.Optional["uic.st01_parse.ParsedST01"] = None
    db_plai: typing.Optional["uic.db_plai_parse.ParsedPLAI"] = None
    bravo: typing.Optional["uic.bravo.BravoRecord"] = None
    pretix: typing.Optional["uic.pretix.Pretix"] = None
    pretix_wallet: typing.Optional["uic.pretix.PretixWallet"] = None
    pretix_totp: typing.Optional["uic.pretix.PretixWallet"] = None
    fpd: typing.Optional["uic.fpd.FixedPointData"] = None
    other_records: typing.List["uic.envelope.Record"] = dataclasses.field(default_factory=list)
    other_dosipas_records: typing.List["uic.dosipas.Record"] = dataclasses.field(default_factory=list)

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
                                    3076,  # Transdev GmbH
                                    3497,  # Regensburger Verkehrsverbund GmbH
                                    5008,  # Verkehrsverbund Rhein-Neckar GmbH
                                    5062,  # Dessauer Verkehrs GmbH
                                    5173,  # Nahverkehrsservice Sachsen-Anhalt GmbH
                                    5197,  # Augsburger Verkehrs- und Tarifverbund GmbH
                            ) or self.dt_ti or self.dt_pa or
                             security_num == 3634  # Deutschlandtarifverbund GmbH
                            ):
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
                    else:
                        return models.Ticket.TYPE_FAHRKARTE
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
            if self.dt_ti.product_name.lower() in ("deutschlandticket", "deutschlandticket job"):
                return models.Ticket.TYPE_DEUTCHLANDTICKET
            return models.Ticket.TYPE_FAHRKARTE
        elif self.vor_fi:
            return models.Ticket.TYPE_FAHRKARTE
        elif self.layout and self.layout.standard in ("RCT2", "RTC2"):
            parser = uic.rct2_parse.RCT2Parser()
            parser.read(self.layout)
            layout = parser.parse(self.issuing_rics())

            dt = layout.document_type.lower()
            if "deutschlandsemesterticket" in dt or \
                    "deutschlandticket" in dt or \
                    "deutschland-ticket" in dt or \
                    "d-ticket" in dt:
                return models.Ticket.TYPE_DEUTCHLANDTICKET

            return models.Ticket.TYPE_FAHRKARTE
        elif self.st01:
            if self.st01.ticket_type == "Deutschlandticket":
                return models.Ticket.TYPE_DEUTCHLANDTICKET
            else:
                return models.Ticket.TYPE_FAHRKARTE
        elif self.db_plai:
            return models.Ticket.TYPE_FAHRKARTE

        return models.Ticket.TYPE_UNKNOWN

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        ticket_type = self.type()

        if ticket_type == models.Ticket.TYPE_DEUTCHLANDTICKET:
            hd.update(b"deutschlandticket")
            hd.update(self.issuer_id())
            if self.flex:
                passenger = self.flex.data.get("travelerDetail", {}).get("traveler", [{}])[0]
                dob_year = passenger.get("yearOfBirth", 0)
                dob_month = passenger.get("monthOfBirth", 0)
                dob_day = passenger.get("dayOfBirthInMonth", 0)
                hd.update(passenger.get("firstName").encode("utf-8"))
                hd.update(passenger.get("lastName").encode("utf-8"))
                hd.update(f"{dob_year:04d}-{dob_month:02d}-{dob_day:02d}".encode("utf-8"))
            elif self.dt_pa:
                hd.update(self.dt_pa.passenger_name.encode("utf-8"))
            elif self.st01:
                if self.st01.passenger_name:
                    hd.update(self.st01.passenger_name.encode("utf-8"))
                if self.st01.passenger_dob:
                    hd.update(self.st01.passenger_dob.isoformat().encode("utf-8"))
            elif self.layout and self.layout.standard in ("RCT2", "RTC2"):
                parser = uic.rct2_parse.RCT2Parser()
                parser.read(self.layout)
                layout = parser.parse(self.issuing_rics())

                if layout.passenger_name:
                    hd.update(layout.passenger_name.encode("utf-8"))
                if layout.date_of_birth:
                    hd.update(layout.date_of_birth.isoformat().encode("utf-8"))
            else:
                hd.update(self.ticket_id().encode("utf-8"))

            return base64.b32hexencode(hd.digest()).decode("utf-8")

        elif ticket_type == models.Ticket.TYPE_BAHNCARD:
            card = self.flex.data["transportDocument"][0]["ticket"][1]
            hd.update(b"bahncard")
            hd.update(self.flex_issuer_id())
            if "cardIdIA5" in card:
                hd.update(card["cardIdIA5"].encode("utf-8"))
            else:
                hd.update(str(card.get("cardIdNum", 0)).encode("utf-8"))
            return base64.b32hexencode(hd.digest()).decode("utf-8")

        elif ticket_type == models.Ticket.TYPE_FAHRKARTE:
            hd.update(b"fahrkarte")
            if self.flex:
                ticket = self.flex.data["transportDocument"][0]["ticket"][1]
                hd.update(self.flex_issuer_id())
                if "referenceIA5" in ticket:
                    hd.update(ticket["referenceIA5"].encode("utf-8"))
                elif "referenceNum" in ticket:
                    hd.update(str(ticket["referenceNum"]).encode("utf-8"))
                else:
                    hd.update(self.ticket_id().encode("utf-8"))
            elif self.st01:
                hd.update(self.issuer_id())
                hd.update(self.st01.ticket_id.encode("utf-8"))
            else:
                hd.update(self.issuer_id())
                hd.update(self.ticket_id().encode("utf-8"))
            return base64.b32hexencode(hd.digest()).decode("utf-8")

        elif ticket_type == models.Ticket.TYPE_RESERVIERUNG:
            ticket = self.flex.data["transportDocument"][0]["ticket"][1]
            hd.update(b"reservierung")
            hd.update(self.flex_issuer_id())
            if self.flex.data["issuingDetail"].get("securityProviderNum") == 1183:
                hd.update(self.flex.data["issuingDetail"].get("issuerPNR", "").encode("utf-8"))
            elif "referenceIA5" in ticket:
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
                ref_parts = interrail_pass["referenceIA5"].split("-")
                if len(ref_parts) == 3:
                    hd.update(ref_parts[0].encode("utf-8"))
                else:
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
            hd.update(self.issuer_id())
            hd.update(self.ticket_id().encode("utf-8"))
            return base64.b32encode(hd.digest()).decode("utf-8")

    def issuing_rics(self) -> int:
        if self.head and self.head.distributing_rics:
            return self.head.distributing_rics

        if self.flex:
            if r := self.flex.issuing_rics():
                return r

        if self.envelope:
            return self.envelope.issuer_rics

        if self.dosipas_envelope and "securityProviderNum" in self.dosipas_envelope.level_2_data["level1Data"]:
            return self.dosipas_envelope.level_2_data["level1Data"]["securityProviderNum"]

        if self.fpd:
            if "issuer" in self.fpd.data and self.fpd.data["issuer"][0] == "rics":
                return self.fpd.data["issuer"][1]

        return 0

    def issuer_id(self) -> bytes:
        if rics := self.issuing_rics():
            return rics.to_bytes(8, "big")

        if self.dosipas_envelope and "securityProviderIA5" in self.dosipas_envelope.level_2_data["level1Data"]:
            return self.dosipas_envelope.level_2_data["level1Data"]["securityProviderIA5"].encode("utf-8")

        if self.fpd:
            if "issuer" in self.fpd.data:
                if self.fpd.data["issuer"][0] == "eraCode":
                    return self.fpd.data["issuer"][1].encode("utf-8")
                elif self.fpd.data["issuer"][0] == "otherCode":
                    v = self.fpd.data["issuer"][1]
                    return f"X{v["codeTable"]}{v["code"]}".encode("utf-8")

        return b""

    def flex_issuer_id(self) -> bytes:
        if "issuerNum" in self.flex.data["issuingDetail"]:
            return self.flex.data["issuingDetail"]["issuerNum"].to_bytes(8, "big")
        elif "issuerIA5" in self.flex.data["issuingDetail"]:
            return self.flex.data["issuingDetail"]["issuerIA5"].encode("utf-8")
        else:
            return b""

    def distributor(self):
        return uic.rics.get_rics(self.issuing_rics())

    def ticket_id(self) -> str:
        if self.head:
            return self.head.ticket_id
        elif self.flex:
            return self.flex.ticket_id()
        elif self.pretix:
            return self.pretix.ticket_id()
        elif self.fpd:
            return self.fpd.id()
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

    def parsed_layout(self) -> typing.Optional[uic.rct2_parse.ParsedRCT2]:
        if self.layout and self.layout.standard in ("RCT2", "RTC2"):
            parser = uic.rct2_parse.RCT2Parser()
            parser.read(self.layout)
            return parser.parse(self.issuing_rics())

        return None

    def dtvg_revoked(self) -> bool:
        return models.DTVGBlocklistItem.objects.filter(
            rics=self.issuing_rics(),
            ticket_id=self.ticket_id(),
        ).count() != 0

    @classmethod
    def from_envelope(
            cls, ticket_bytes: bytes, ticket_envelope: uic.Envelope,
            context: "TicketContexts"
    ) -> "UICTicket":
        layout = parse_ticket_uic_layout(ticket_envelope)
        st01 = None
        db_plai = None
        if layout and layout.standard == "ST01":
            parser = uic.st01_parse.ST01Parser()
            parser.read(layout)
            st01 = parser.parse()
        elif layout and layout.standard == "PLAI" and ticket_envelope.issuer_rics == 80:
            parser = uic.db_plai_parse.PLAIParser()
            parser.read(layout)
            db_plai = parser.parse()

        return cls(
            raw_bytes=ticket_bytes,
            envelope=ticket_envelope,
            head=parse_ticket_uic_head(ticket_envelope),
            layout=layout,
            flex=parse_ticket_uic_flex(ticket_envelope),
            dt_ti=parse_ticket_uic_dt_ti(ticket_envelope),
            dt_pa=parse_ticket_uic_dt_pa(ticket_envelope),
            db_bl=parse_ticket_uic_db_bl(ticket_envelope),
            db_vu=parse_ticket_uic_db_vu(ticket_envelope, context),
            cd_ut=parse_ticket_uic_cd_ut(ticket_envelope, context),
            oebb_99=parse_ticket_uic_oebb_99(ticket_envelope),
            vor_fi=parse_ticket_uic_vor_fi(ticket_envelope),
            vor_vd=parse_ticket_uic_vor_vd(ticket_envelope),
            vor_fk=parse_ticket_uic_vor_fk(ticket_envelope),
            bravo=parse_ticket_uic_bravo(ticket_envelope),
            pretix=parse_ticket_uic_pretix(ticket_envelope),
            pretix_wallet=parse_ticket_uic_pretix_wallet(ticket_envelope),
            st01=st01,
            db_plai=db_plai,
            other_records=[r for r in ticket_envelope.records if not (
                    r.id.startswith("U_") or r.id == "0080BL" or r.id == "0080VU"
                    or r.id == "1154UT" or r.id == "118199"
                    or r.id == "5197TI" or r.id == "5197PA"
                    or r.id == "5008TI" or r.id == "5008PA"
                    or r.id == "3497TI" or r.id == "3497PA"
                    or r.id == "5245TI" or r.id == "5245PA"
                    or r.id == "3565TI" or r.id == "3565PA"
                    or r.id == "3306FI" or r.id == "3306VD" or r.id == "3306FK"
                    or r.id == "3606AA" or r.id == "3697OT"
                    or r.id == "000IVU" or r.id == "CXX___"
                    or r.id == "3602AA"
                    or r.id == "5101PX" or r.id == "5101PW"
            )]
        )

    @classmethod
    def from_dosipas(
            cls, ticket_bytes: bytes, dosipas: uic.DOSIPASEnvelope,
            _context: "TicketContexts"
    ) -> "UICTicket":
        records = list(dosipas.records)
        if dosipas.level_2_record:
            records += [dosipas.level_2_record]

        return cls(
            raw_bytes=ticket_bytes,
            dosipas_envelope=dosipas,
            flex=parse_ticket_uic_flex_dosipas(dosipas),
            dosipas_dcd=parse_ticket_uic_dosipas_dcd(dosipas),
            pretix=parse_ticket_uic_dosipas_pretix(dosipas),
            pretix_wallet=parse_ticket_uic_dosipas_pretix_wallet(dosipas),
            pretix_totp=parse_ticket_uic_dosipas_pretix_totp(dosipas),
            fpd=parse_ticket_uic_dosipas_fpd(dosipas),
            other_dosipas_records=[r for r in records if not (
                    r.format.startswith("FCB") or r.format.startswith("FDC")
                    or r.format == "_5101PTIX" or r.format == "_5101PXW"
                    or r.format == "_5101TOTP"
                    or r.format == "_3896FPD0"
            )],
        )


@dataclasses.dataclass
class TS2Ticket:
    raw_bytes: bytes
    envelope: ts2.Envelope
    data: ts2.TicketData

    @property
    def ticket_type(self) -> str:
        return "TS2"

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"ts2")
        hd.update(self.envelope.issuer_rics.to_bytes(4, "big"))
        hd.update(self.data.ticket_id.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")

    def distributor(self):
        return uic.rics.get_rics(self.envelope.issuer_rics)

    @classmethod
    def from_envelope(
            cls, ticket_bytes: bytes, ticket_envelope: uic.Envelope,
    ) -> "TS2Ticket":
        data = parse_ticket_ts2_data(ticket_envelope)

        return cls(
            raw_bytes=ticket_bytes,
            envelope=ticket_envelope,
            data=data,
        )


@dataclasses.dataclass
class RSPTicket:
    rsp_type: str
    issuer_id: str
    ticket_ref: str
    utn_data: typing.Optional[rsp.utn.UTN]
    raw_ticket: bytes
    data: typing.Union[rsp.RailcardData, rsp.TicketData, rsp.Type11]

    @property
    def ticket_type(self) -> str:
        return "RSP"

    def type(self) -> str:
        if self.rsp_type == "08":
            return models.Ticket.TYPE_RAILCARD
        elif self.rsp_type == "06":
            return models.Ticket.TYPE_FAHRKARTE
        elif self.rsp_type == "11":
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
        hd.update(self.data.coupon_type.value.to_bytes(1, "big"))
        return base64.b32encode(hd.digest()).decode("utf-8")

    @property
    def rsp_type_name(self):
        if self.rsp_type == "08":
            return "Railcard"
        elif self.rsp_type == "06":
            return "Ticket"
        elif self.rsp_type == "11":
            return "Ticket (small)"
        else:
            return "Unknown"

    @property
    def raw_ticket_hex(self):
        return ":".join(f"{b:02x}" for b in self.raw_ticket)

    def issuer_name(self):
        return rsp.issuers.issuer_name(self.issuer_id)


@dataclasses.dataclass
class FlexiTicket:
    issuer_id: str
    ticket_data: typing.Optional[flexi_ticket.Data] = None
    raw_ticket: typing.Optional[bytes] = None
    extra_data: typing.Optional[flexi_ticket.Data] = None
    raw_extra_data: typing.Optional[bytes] = None

    @property
    def ticket_type(self) -> str:
        return "FT"

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"ft")
        hd.update(self.issuer_id.encode("utf-8"))
        if self.ticket_data:
            hd.update(self.ticket_data.E_TICKET_NUMBER.encode("utf-8"))
        elif self.extra_data:
            hd.update(int(self.extra_data.ACTIVATION_START_UTC_DATE_TIME.timestamp()).to_bytes(8, "big"))
        return base64.b32encode(hd.digest()).decode("utf-8")

    @property
    def raw_ticket_hex(self):
        return ":".join(f"{b:02x}" for b in self.raw_ticket)

    @property
    def raw_extra_data_hex(self):
        return ":".join(f"{b:02x}" for b in self.raw_extra_data)

    @property
    def issuer_name(self):
        if self.issuer_id == "M0":
            return "Massachusetts Bay Transportation Authority"
        elif self.issuer_id == "MA":
            return "New York Metropolitan Transportation Authority"
        elif self.issuer_id == "RP":
            return "Denver Regional Transportation District"
        elif self.issuer_id == "ML":
            return "Metrolink"
        else:
            return None

    @property
    def brand_id(self):
        if self.issuer_id == "M0":
            return "MBTA"
        elif self.issuer_id == "MA":
            return "MTA"
        elif self.issuer_id == "RP":
            return "RTDDENVER"
        elif self.issuer_id == "ML":
            return "ML"
        else:
            return None


@dataclasses.dataclass
class SNCFTicket:
    raw_ticket: bytes
    data: sncf.SNCFTicket

    @property
    def ticket_type(self) -> str:
        return "SNCF"

    @staticmethod
    def type() -> str:
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

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"elb")
        hd.update(self.data.pnr.encode("utf-8"))
        hd.update(self.data.booking_number.encode("utf-8"))
        hd.update(self.data.sequence_number.to_bytes(2, "big"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class SSBTicket:
    raw_ticket: bytes
    envelope: ssb.Envelope
    data: typing.Union[
        ssb.NonReservationTicket, ssb.IntegratedReservationTicket,
        ssb.GroupTicket, ssb.ns_keycard.Keycard,
        ssb.sz.Ticket, ssb.cd.Ticket,
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
        elif isinstance(self.data, ssb.cd.Ticket):
            return models.Ticket.TYPE_FAHRKARTE
        else:
            return models.Ticket.TYPE_UNKNOWN

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"ssb")
        hd.update(self.envelope.issuer_rics.to_bytes(8, "big"))
        hd.update(self.envelope.ticket_type.to_bytes(8, "big"))
        if isinstance(self.data, ssb.sz.Ticket):
            hd.update(self.data.unique_ticket_id.to_bytes(8, "big"))
            for e in self.data.extras:
                hd.update(e.unique_extra_id.to_bytes(8, "big"))
        else:
            hd.update(self.data.pnr.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class SSB1Ticket:
    raw_ticket: bytes
    ticket: ssb1.Ticket

    @property
    def ticket_type(self) -> str:
        return "SSB1"

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"ssb1")
        hd.update(self.ticket.issuer_rics.to_bytes(8, "big"))
        hd.update(self.ticket.pnr.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class HZPPTicket:
    raw_ticket: bytes
    data: hzpp.HZPPTicket

    @property
    def ticket_type(self) -> str:
        return "HZPP"

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"hzpp")
        hd.update(self.data.ticket_number.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class SwissPassTicket:
    raw_ticket: bytes
    data: swisspass.SwissPassTicket

    @property
    def ticket_type(self) -> str:
        return "SwissPass"

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"swisspass")
        hd.update(self.data.ticket.ticket_data.ticket_id.to_bytes(8, "big"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class IATATicket:
    raw_ticket: bytes
    data: iata.Envelope

    @property
    def ticket_type(self) -> str:
        return "IATA"

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_BORDKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"iata")
        for leg in self.data.legs:
            if leg.operating_carrier == "UPX":
                hd.update(b"upx")
                hd.update(leg.airline_data.encode("utf-8"))
            else:
                hd.update(leg.pnr.encode("utf-8"))
                hd.update(leg.sequence.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class BahnBonusCode:
    raw_ticket: bytes
    data: bahnbonus.BahnBonusCode

    @property
    def ticket_type(self) -> str:
        return "BahnBonus"

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_BAHNBONUS

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"bahnbonus")
        hd.update(self.data.barcode_id.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class SNCBTrainPlus:
    raw_ticket: bytes
    data: sncb_train_plus.TrainPlusCode

    @property
    def ticket_type(self) -> str:
        return "SNCBTrainPlus"

    @property
    def raw_ticket_str(self):
        return self.raw_ticket.decode("utf-8", "replace")

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_BAHNCARD

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"sncb-train-plus")
        hd.update(self.data.card_number.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")


@dataclasses.dataclass
class ADIFTicket:
    raw_ticket: bytes
    ticket_ref: int
    issuer_id: int
    data: adif.Ticket

    @property
    def ticket_type(self) -> str:
        return "ADIF"

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"adif")
        hd.update(self.data.issuer_id.to_bytes(8, "big"))
        hd.update(self.data.ticket_ref.to_bytes(8, "big"))
        return base64.b32encode(hd.digest()).decode("utf-8")

    def distributor(self):
        return uic.rics.get_rics(self.issuer_id)


@dataclasses.dataclass
class MavTicket:
    raw_bytes: bytes
    envelope: mav.Envelope
    data: mav.TicketData

    @property
    def ticket_type(self) -> str:
        return "MAV"

    @staticmethod
    def type() -> str:
        return models.Ticket.TYPE_FAHRKARTE

    def pk(self) -> str:
        hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)

        hd.update(b"mav")
        hd.update(self.envelope.issuer_rics.to_bytes(4, "big"))
        hd.update(self.envelope.ticket_id.encode("utf-8"))
        return base64.b32encode(hd.digest()).decode("utf-8")

    def distributor(self):
        return uic.rics.get_rics(self.envelope.issuer_rics)

    @classmethod
    def from_envelope(
            cls, ticket_bytes: bytes, ticket_envelope: mav.Envelope,
    ) -> "MavTicket":
        data = parse_ticket_mav_data(ticket_envelope)

        return cls(
            raw_bytes=ticket_bytes,
            envelope=ticket_envelope,
            data=data,
        )


def parse_ticket_vdv(ticket_bytes: bytes, context: "TicketContexts") -> VDVTicket:
    pki_store = vdv.get_pki_store()

    try:
        motics = vdv.Motics.parse(ticket_bytes)
        envelope = vdv.EnvelopeV2.parse(motics.application_data)
    except vdv.motics.NotAMoticsException:
        try:
            motics = None
            envelope = vdv.EnvelopeV2.parse(ticket_bytes)
        except vdv.util.VDVException:
            raise TicketError(
                title="This doesn't look like a valid VDV ticket",
                message="You may have scanned something that is not a VDV ticket, the ticket is corrupted, or there "
                        "is a bug in this program.",
                exception=traceback.format_exc()
            )
    except vdv.util.VDVException:
        raise TicketError(
            title="This doesn't look like a valid VDV Motics ticket",
            message="You may have scanned something that is not a VDV Motics ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    raw_issuing_ca = pki_store.find_certificate(envelope.ca_reference)
    if not raw_issuing_ca:
        raise TicketError(
            title="Unknown issuing certificate",
            message="The certificate that issued this ticket is not known - the ticket is likely invalid."
        )

    if raw_issuing_ca.level == 3:
        root_ca_ref = vdv.CAReference.level_3_root()
    elif raw_issuing_ca.level == 2:
        root_ca_ref = vdv.CAReference.level_2_root()
    elif raw_issuing_ca.level == 1:
        root_ca_ref = vdv.CAReference.level_1_root()
    else:
        raise NotImplementedError()
    raw_root_ca = pki_store.find_certificate(root_ca_ref)
    if not raw_root_ca:
        raise TicketError(
            title="Internal error",
            message="The root CA couldn't be found. This is almost certainly a bug.",
        )

    try:
        root_ca = vdv.Certificate.parse(raw_root_ca.data)
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

    if root_ca_data.ca_reference != root_ca_ref or root_ca_data.certificate_holder_reference != root_ca_ref:
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
        issuing_ca = vdv.Certificate.parse(raw_issuing_ca.data)
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

    tickets = []
    for authorization in envelope.authorizations:
        try:
            ticket_data = authorization.decrypt_with_cert(envelope_certificate_data)
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

        tickets.append((ticket_data, ticket))

    if not tickets:
        raise TicketError(
            title="No tickets found",
            message="This barcode contains no tickets.",
        )

    return VDVTicket(
        root_ca=root_ca_data,
        issuing_ca=issuing_ca_data,
        envelope_certificate=envelope_certificate_data,
        raw_ticket=tickets[0][0],
        ticket=tickets[0][1],
        motics=motics,
    )


def parse_ticket_uic_head(ticket_envelope: uic.Envelope) -> typing.Optional[uic.HeadV1]:
    head_record = next(filter(lambda r: r.id == "U_HEAD", ticket_envelope.records), None)
    if not head_record:
        return None

    if head_record.version not in (0, 1):
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

    if layout_record.version not in (0, 1):
        raise TicketError(
            title="Unsupported layout record version",
            message=f"The layout record version {layout_record.version} is not supported."
        )

    try:
        return uic.LayoutV1.parse(layout_record.data, ticket_envelope.issuer_rics, layout_record.is_utf8_len)
    except uic.util.UICException:
        raise TicketError(
            title="Invalid layout record",
            message="The layout record can't be parsed - the ticket is likely invalid.",
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
            message="The flexible record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_flex_dosipas(ticket_envelope: uic.DOSIPASEnvelope) -> typing.Optional[uic.Flex]:
    flex_record = next(filter(lambda r: r.format.startswith("FCB"), ticket_envelope.records), None)
    if not flex_record:
        return None

    try:
        version = int(flex_record.format[3:])
        return uic.Flex.parse(version, flex_record.data)
    except (ValueError, uic.util.UICException):
        raise TicketError(
            title="Invalid flexible data record",
            message="The flexible record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_dosipas_dcd(ticket_envelope: uic.DOSIPASEnvelope) -> typing.Optional["uic.dosipas.DCD"]:
    if not ticket_envelope.level_2_record or not ticket_envelope.level_2_record.format.startswith("FDC"):
        return None

    try:
        version = int(ticket_envelope.level_2_record.format[3:])
        return uic.dosipas.DCD.parse(version, ticket_envelope.level_2_record.data)
    except (ValueError, uic.util.UICException):
        raise TicketError(
            title="Invalid dynamic data record",
            message="The dynamic record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_dt_ti(ticket_envelope: uic.Envelope) -> typing.Optional["uic.dt.DTRecordTI"]:
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
            message="The TI record is can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_dt_pa(ticket_envelope: uic.Envelope) -> typing.Optional["uic.dt.DTRecordTI"]:
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
            message="The PA record is can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_db_bl(ticket_envelope: uic.Envelope) -> typing.Optional["uic.db.DBRecordBL"]:
    bl_record = next(filter(lambda r: r.id == "0080BL", ticket_envelope.records), None)
    if not bl_record:
        return None

    try:
        r = uic.db.DBRecordBL.parse(bl_record.data, bl_record.version)
        print(r)
        return r
    except uic.db.DBException:
        raise TicketError(
            title="Invalid DB BL record",
            message="The DB BL record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_cd_ut(
        ticket_envelope: uic.Envelope, context: TicketContexts
) -> typing.Optional["uic.cd.CDRecordUT"]:
    ut_record = next(
        filter(lambda r: (r.id == "1154UT" or r.id == "3697OT") and r.version == 1, ticket_envelope.records), None)
    if not ut_record:
        return None

    try:
        return uic.cd.CDRecordUT.parse(ut_record.data, ut_record.version, context)
    except uic.cd.CDException:
        raise TicketError(
            title="Invalid CD UT record",
            message="The CD UT record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_db_vu(
        ticket_envelope: uic.Envelope, context: TicketContexts
) -> typing.Optional["uic.db_vu.DBRecordVU"]:
    vu_record = next(filter(lambda r: r.id == "0080VU" and r.version == 1, ticket_envelope.records), None)
    if not vu_record:
        return None

    try:
        return uic.db_vu.DBRecordVU.parse(vu_record.data, vu_record.version, context)
    except uic.db_vu.DBVUException:
        raise TicketError(
            title="Invalid DB VU Record",
            message="The DB VU record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_oebb_99(ticket_envelope: uic.Envelope) -> typing.Optional["uic.oebb.OeBBRecord99"]:
    oebb_record = next(
        filter(lambda r: (r.id == "118199" or r.id == "3602AA") and r.version == 1, ticket_envelope.records), None)
    if not oebb_record:
        return None

    try:
        return uic.oebb.OeBBRecord99.parse(oebb_record.data, oebb_record.version)
    except uic.oebb.OeBBException:
        raise TicketError(
            title="Invalid ÖBB 99 record",
            message="The ÖBB 99 record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_vor_fi(ticket_envelope: uic.Envelope) -> typing.Optional["uic.vor.VORRecordFI"]:
    vor_record = next(filter(lambda r: r.id == "3306FI" and r.version == 1, ticket_envelope.records), None)
    if not vor_record:
        return None

    try:
        return uic.vor.VORRecordFI.parse(vor_record.data, vor_record.version)
    except uic.vor.VORRecordFI:
        raise TicketError(
            title="Invalid VOR FI record",
            message="The VOR FI record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_vor_vd(ticket_envelope: uic.Envelope) -> typing.Optional["uic.vor.VORRecordVD"]:
    vor_record = next(filter(lambda r: r.id == "3306VD" and r.version == 1, ticket_envelope.records), None)
    if not vor_record:
        return None

    try:
        return uic.vor.VORRecordVD.parse(vor_record.data, vor_record.version)
    except uic.vor.VORException:
        raise TicketError(
            title="Invalid VOR VD record",
            message="The VOR VD record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_vor_fk(ticket_envelope: uic.Envelope) -> typing.Optional["uic.vor.VORRecordFK"]:
    vor_record = next(filter(lambda r: r.id == "3306FK" and r.version == 1, ticket_envelope.records), None)
    if not vor_record:
        return None

    try:
        return uic.vor.VORRecordFK.parse(vor_record.data, vor_record.version)
    except uic.vor.VORException:
        raise TicketError(
            title="Invalid VOR FK record",
            message="The VOR FK record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_bravo(ticket_envelope: uic.Envelope) -> typing.Optional["uic.bravo.BravoRecord"]:
    bravo_record = next(filter(lambda r: r.id in ("000IVU", "CXX___") and r.version == 1, ticket_envelope.records),
                        None)
    if not bravo_record:
        return None

    try:
        return uic.bravo.BravoRecord.parse(bravo_record.data)
    except uic.bravo.BravoException:
        raise TicketError(
            title="Invalid Bravo data",
            message="The Bravo data is can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_pretix(ticket_envelope: uic.Envelope) -> typing.Optional["uic.pretix.Pretix"]:
    pretix_record = next(filter(lambda r: r.id == "5101PX" and r.version == 1, ticket_envelope.records), None)
    if not pretix_record:
        return None

    try:
        return uic.pretix.Pretix.parse(pretix_record.data)
    except uic.UICException:
        raise TicketError(
            title="Invalid Pretix data",
            message="The Pretix data is can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_dosipas_pretix(ticket_envelope: uic.DOSIPASEnvelope) -> typing.Optional["uic.pretix.Pretix"]:
    pretix_record = next(filter(lambda r: r.format == "_5101PTIX", ticket_envelope.records), None)
    if not pretix_record:
        return None

    try:
        return uic.pretix.Pretix.parse(pretix_record.data)
    except uic.UICException:
        raise TicketError(
            title="Invalid Pretix data",
            message="The Pretix data is can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_pretix_wallet(ticket_envelope: uic.Envelope) -> typing.Optional["uic.pretix.PretixWallet"]:
    pretix_record = next(filter(lambda r: r.id == "5101PW" and r.version == 1, ticket_envelope.records), None)
    if not pretix_record:
        return None

    try:
        return uic.pretix.PretixWallet.parse(pretix_record.data)
    except uic.UICException:
        raise TicketError(
            title="Invalid Pretix data",
            message="The Pretix wallet data is can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_dosipas_pretix_wallet(ticket_envelope: uic.DOSIPASEnvelope) -> typing.Optional[
    "uic.pretix.PretixWallet"]:
    pretix_record = next(filter(lambda r: r.format == "_5101PXW", ticket_envelope.records), None)
    if not pretix_record:
        return None

    try:
        return uic.pretix.PretixWallet.parse(pretix_record.data)
    except uic.UICException:
        raise TicketError(
            title="Invalid Pretix data",
            message="The Pretix wallet data is can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_dosipas_pretix_totp(ticket_envelope: uic.DOSIPASEnvelope) -> typing.Optional["uic.pretix.PretixTOTP"]:
    if not ticket_envelope.level_2_record or not ticket_envelope.level_2_record.format == "_5101TOTP":
        return None

    try:
        return uic.pretix.PretixTOTP.parse(ticket_envelope.level_2_record.data)
    except uic.util.UICException:
        raise TicketError(
            title="Invalid Pretix TOTP",
            message="The TOTP record can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic_dosipas_fpd(ticket_envelope: uic.DOSIPASEnvelope) -> typing.Optional["uic.fpd.FixedPointData"]:
    # Temp ID until standardised
    record = next(filter(lambda r: r.format == "_3896FPD0", ticket_envelope.records), None)
    if not record:
        return None

    try:
        return uic.fpd.FixedPointData.parse(record.data)
    except uic.util.UICException:
        raise TicketError(
            title="Invalid UIC Fixed Point Data",
            message="The FPD can't be parsed - the data is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_uic(ticket_bytes: bytes, context: TicketContexts) -> UICTicket:
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


def parse_ticket_uic_qr(ticket_bytes: bytes, context: TicketContexts) -> UICTicket:
    try:
        ticket = ticket_bytes.decode("ascii")
    except UnicodeDecodeError:
        raise TicketError(
            title="This doesn't look like a valid UIC QR ticket",
            message="You may have scanned something that is not a UIC QR ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    parts = ticket.split(":", 2)
    if len(parts) != 3:
        raise TicketError(
            title="This doesn't look like a valid UIC QR ticket",
            message="There aren't enough sections to this ticket's header."
        )

    _, encoding, data = parts

    if encoding != "B45":
        raise TicketError(
            title="Unsupported UIC QR encoding",
            message=f"The encoding method {encoding} is not supported yet."
        )

    try:
        ticket_bytes = base45.b45decode(data)
    except ValueError:
        raise TicketError(
            title="This doesn't look like a valid UIC QR ticket",
            message="The Base45 encoding couldn't be read.",
            exception=traceback.format_exc()
        )

    if dosipas := uic.DOSIPASEnvelope.decode(ticket_bytes):
        return UICTicket.from_dosipas(ticket_bytes, dosipas, context)

    return parse_ticket_uic(ticket_bytes, context)


def parse_ticket_uic_url(ticket_bytes: bytes, context: TicketContexts) -> UICTicket:
    try:
        ticket = ticket_bytes.decode("ascii")
    except UnicodeDecodeError:
        raise TicketError(
            title="This doesn't look like a valid UIC URL",
            message="You may have scanned something that is not a UIC URL, it is corrupted, or there is a bug in this program.",
            exception=traceback.format_exc()
        )

    match = UIC_URL_RE.fullmatch(ticket)
    if not match:
        raise TicketError(
            title="This doesn't look like a valid UIC URL",
            message="You may have scanned something that is not a UIC URL, it is corrupted, or there is a bug in this program.",
        )

    data = match.group(1)
    data = base_decode(data, UIC_URL_ALPHABET)

    if dosipas := uic.DOSIPASEnvelope.decode(data):
        return UICTicket.from_dosipas(data, dosipas, context)

    return parse_ticket_uic(data, context)


def parse_ticket_ts2(ticket_bytes: bytes) -> TS2Ticket:
    try:
        ticket_envelope = ts2.Envelope.parse(ticket_bytes)
    except ts2.util.TS2Exception:
        raise TicketError(
            title="Invalid TS2 data",
            message="The TS2 ticket envelope can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )

    return TS2Ticket.from_envelope(ticket_bytes, ticket_envelope)


def parse_ticket_ts2_data(ticket_envelope: ts2.Envelope) -> ts2.TicketData:
    try:
        return ts2.TicketData.parse(ticket_envelope.data)
    except ts2.util.TS2Exception:
        raise TicketError(
            title="Invalid TS2 data",
            message="The TS2 ticket contents can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )


def parse_ticket_rsp(ticket_bytes: bytes) -> RSPTicket:
    pki_store = rsp.get_pki_store()

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

    try:
        if ticket_envelope.ticket_type == "08":
            data = rsp.RailcardData.parse(ticket_payload)
        elif ticket_envelope.ticket_type == "06":
            data = rsp.TicketData.parse(ticket_payload)
        else:
            raise TicketError(
                title="Unsupported RSP ticket type",
                message=f"We don't know how to parse type {ticket_envelope.ticket_type} tickets",
            )
    except rsp.RSPException:
        raise TicketError(
            title="This doesn't look like a valid RSP ticket",
            message="You may have scanned something that is not a RSP ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    try:
        utn_data = rsp.utn.UTN.from_int(rsp.utn.decode_base30(ticket_envelope.ticket_ref))
    except ValueError:
        utn_data = None

    return RSPTicket(
        rsp_type=ticket_envelope.ticket_type,
        ticket_ref=ticket_envelope.ticket_ref,
        issuer_id=ticket_envelope.issuer_id,
        utn_data=utn_data,
        raw_ticket=ticket_payload,
        data=data
    )


def parse_ticket_rsp_11(ticket_bytes: bytes) -> RSPTicket:
    try:
        data = rsp.Type11.parse(ticket_bytes)
    except rsp.RSPException:
        raise TicketError(
            title="This doesn't look like a valid RSP ticket",
            message="You may have scanned something that is not a RSP ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    try:
        utn_data = rsp.utn.UTN.from_int(rsp.utn.decode_base30(data.ticket_ref))
    except ValueError:
        utn_data = None

    return RSPTicket(
        rsp_type=data.barcode_type,
        ticket_ref=data.ticket_ref,
        issuer_id=data.issuer_id,
        utn_data=utn_data,
        raw_ticket=ticket_bytes,
        data=data
    )


def parse_ticket_flexi_ticket(ticket_bytes: bytes) -> FlexiTicket:
    pki_store = flexi_ticket.get_pki_store()

    try:
        ticket_envelope = flexi_ticket.Envelope.parse(ticket_bytes)
    except flexi_ticket.FTException:
        raise TicketError(
            title="This doesn't look like a valid flexi-ticket",
            message="You may have scanned something that is not a flexi-ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    ticket_payload = None
    if ticket_envelope.issuer_id in pki_store.certificates:
        for cert in pki_store.certificates[ticket_envelope.issuer_id]:
            try:
                ticket_payload = ticket_envelope.decrypt_with_cert(cert)
            except flexi_ticket.FTException:
                raise TicketError(
                    title="Unable to decrypt flexi-ticket",
                    message="Its likely the signature over this ticket has been forged - the ticket is invalid.",
                    exception=traceback.format_exc()
                )
            if ticket_payload:
                break

    try:
        ticket_extra_data = ticket_envelope.decrypt_extra_data()
    except flexi_ticket.FTException:
        raise TicketError(
            title="Unable to decrypt flexi-ticket",
            message="The additional data for this ticket cannot be read - the ticket is invalid.",
            exception=traceback.format_exc()
        )

    if ticket_payload:
        try:
            ticket_data = flexi_ticket.Data.parse(ticket_payload, ticket_envelope.issuer_id)
        except flexi_ticket.FTException:
            raise TicketError(
                title="This doesn't look like a valid flex-ticket",
                message="You may have scanned something that is not a flexi-ticket, the ticket is corrupted, or there "
                        "is a bug in this program.",
                exception=traceback.format_exc()
            )
    else:
        ticket_data = None

    if ticket_extra_data:
        try:
            extra_data = flexi_ticket.Data.parse(ticket_extra_data, ticket_envelope.issuer_id)
        except flexi_ticket.FTException:
            raise TicketError(
                title="This doesn't look like a valid flex-ticket",
                message="You may have scanned something that is not a flexi-ticket, the ticket is corrupted, or there "
                        "is a bug in this program.",
                exception=traceback.format_exc()
            )
    else:
        extra_data = None

    return FlexiTicket(
        issuer_id=ticket_envelope.issuer_id,
        ticket_data=ticket_data,
        extra_data=extra_data,
        raw_ticket=ticket_payload,
        raw_extra_data=ticket_extra_data,
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


def parse_ticket_ssb(ticket_bytes: bytes, context: TicketContexts) -> SSBTicket:
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
        data = ssb.IntegratedReservationTicket.parse(envelope.data, envelope.issuer_rics, context)
    elif envelope.ticket_type == 2:
        data = ssb.NonReservationTicket.parse(envelope.data, envelope.issuer_rics, context)
    elif envelope.ticket_type == 3:
        data = ssb.GroupTicket.parse(envelope.data, envelope.issuer_rics)
    elif envelope.ticket_type == 4:
        data = ssb.Pass.parse(envelope.data)
    elif envelope.issuer_rics == 1184 and envelope.ticket_type == 21:
        data = ssb.ns_keycard.Keycard.parse(envelope.data)
    elif envelope.issuer_rics == 1179 and envelope.ticket_type == 21:
        data = ssb.sz.Ticket.parse(envelope.data, envelope.version)
    elif envelope.issuer_rics == 1154 and envelope.ticket_type == 24:
        data = ssb.cd.Ticket.parse(envelope.data)
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


def parse_ticket_hzpp(ticket_bytes: bytes) -> HZPPTicket:
    try:
        data = hzpp.HZPPTicket.parse(ticket_bytes)
    except hzpp.HZPPException:
        raise TicketError(
            title="This doesn't look like a valid HŽPP ticket",
            message="You may have scanned something that is not an HŽPP ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    return HZPPTicket(
        raw_ticket=ticket_bytes,
        data=data
    )


def parse_ticket_swiss_pass(ticket_bytes: bytes) -> SwissPassTicket:
    try:
        data = swisspass.SwissPassTicket.parse(ticket_bytes)
    except swisspass.SwissPassException:
        raise TicketError(
            title="This doesn't look like a valid SwissPass ticket",
            message="You may have scanned something that is not an SwissPass ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    return SwissPassTicket(
        raw_ticket=ticket_bytes,
        data=data
    )


def parse_ticket_iata(ticket_bytes: bytes, _context: TicketContexts) -> IATATicket:
    try:
        data = iata.Envelope.parse(ticket_bytes)
    except iata.IATAException:
        raise TicketError(
            title="This doesn't look like a valid IATA ticket",
            message="You may have scanned something that is not an IATA ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    return IATATicket(
        raw_ticket=ticket_bytes,
        data=data
    )


def parse_bahn_bonus(ticket_bytes: bytes) -> BahnBonusCode:
    try:
        data = bahnbonus.BahnBonusCode.parse(ticket_bytes)
    except bahnbonus.BahnBonusException:
        raise TicketError(
            title="This doesn't look like a valid BahnBonus code",
            message="You may have scanned something that is not an BahnBonus code, "
                    "the code is corrupted, or there is a bug in this program.",
            exception=traceback.format_exc()
        )

    return BahnBonusCode(
        raw_ticket=ticket_bytes,
        data=data
    )


def parse_sncb_train_plus(ticket_bytes: bytes) -> SNCBTrainPlus:
    try:
        data = sncb_train_plus.TrainPlusCode.parse(ticket_bytes)
    except sncb_train_plus.SNCBTrainPlusException:
        raise TicketError(
            title="This doesn't look like a valid SNCB train plus barcode",
            message="You may have scanned something that is not a SNCB train plus barcode, "
                    "the code is corrupted, or there is a bug in this program.",
            exception=traceback.format_exc()
        )

    return SNCBTrainPlus(
        raw_ticket=ticket_bytes,
        data=data
    )


def parse_ticket_adif(ticket_bytes: bytes) -> ADIFTicket:
    try:
        data = adif.Ticket.parse(ticket_bytes)
    except adif.ADIFException:
        raise TicketError(
            title="This doesn't look like a valid ADIF ticket",
            message="You may have scanned something that is not a ADIF ticket, "
                    "the ticket is corrupted, or there is a bug in this program.",
            exception=traceback.format_exc()
        )

    return ADIFTicket(
        ticket_ref=data.ticket_ref,
        issuer_id=data.issuer_id,
        raw_ticket=ticket_bytes,
        data=data
    )


def parse_ticket_mav(ticket_bytes: bytes) -> MavTicket:
    try:
        data = mav.Envelope.parse(ticket_bytes)
    except mav.MavException:
        raise TicketError(
            title="This doesn't look like a valid MÁV ticket",
            message="You may have scanned something that is not an MÁV ticket, the ticket is corrupted, or there "
                    "is a bug in this program.",
            exception=traceback.format_exc()
        )

    return MavTicket.from_envelope(ticket_bytes, data)


def parse_ticket_mav_data(ticket_envelope: mav.Envelope) -> mav.TicketData:
    try:
        return mav.TicketData.parse(ticket_envelope)
    except mav.MavException:
        raise TicketError(
            title="Invalid MÁV data",
            message="The MÁV ticket contents can't be parsed - the ticket is likely invalid.",
            exception=traceback.format_exc()
        )



def parse_ticket(
        ticket_bytes: bytes, account: typing.Optional["models.Account"]
) -> typing.Union[
    VDVTicket, UICTicket, RSPTicket, SNCFTicket, ELBTicket, SSBTicket,
    SSB1Ticket, HZPPTicket, SwissPassTicket, IATATicket, BahnBonusCode,
    FlexiTicket, TS2Ticket, SNCBTrainPlus, ADIFTicket, MavTicket
]:
    context = account.ticket_contexts() if account else TicketContexts([])
    if len(ticket_bytes) == 114 and (ticket_bytes[0] & 0xF0) >> 4 == 3:
        return parse_ticket_ssb(ticket_bytes, context)

    try:
        d = base64.b64decode(ticket_bytes, validate=True)

        if d[:3] == b"#UT":
            return parse_ticket_uic(d, context)
        elif (d[0] & 0xF0) >> 4 in (2, 3):
            return parse_ticket_ssb(d, context)
    except binascii.Error:
        pass

    if len(ticket_bytes) == 107 and (ticket_bytes[0] & 0xF0) >> 4 in (1, 2):
        return parse_ticket_ssb1(ticket_bytes)

    if bahnbonus.is_bahnbonus_code(ticket_bytes):
        return parse_bahn_bonus(ticket_bytes)

    if ticket_bytes[:4] == b"i0CV":
        return parse_ticket_sncf(ticket_bytes)

    if ticket_bytes[:3] == b"#UT":
        return parse_ticket_uic(ticket_bytes, context)

    if ticket_bytes[:3] == b"TS2":
        return parse_ticket_ts2(ticket_bytes)

    if ticket_bytes[:4] == b"UIC:":
        return parse_ticket_uic_qr(ticket_bytes, context)

    if len(ticket_bytes) == 516:
        return parse_ticket_adif(ticket_bytes)

    if ticket_bytes[:2] in (b"06", b"08"):
        return parse_ticket_rsp(ticket_bytes)

    if ticket_bytes[:2] == b"FT":
        return parse_ticket_flexi_ticket(ticket_bytes)

    if ticket_bytes[:2] in (b"A1", b"B1"):
        return parse_ticket_hzpp(ticket_bytes)

    if ticket_bytes[:1] == b"e":
        return parse_ticket_elb(ticket_bytes)

    if ticket_bytes[:1] == b"M":
        return parse_ticket_iata(ticket_bytes, context)

    if ticket_bytes[0] == 0x0a:
        return parse_ticket_swiss_pass(ticket_bytes)

    if ticket_bytes[0] == 0x06:
        return parse_ticket_mav(ticket_bytes)

    if dosipas := uic.DOSIPASEnvelope.decode(ticket_bytes):
        return UICTicket.from_dosipas(ticket_bytes, dosipas, context)

    if sncb_train_plus.is_sncb_train_plus_code(ticket_bytes):
        return parse_sncb_train_plus(ticket_bytes)

    if b"$UIC:" in ticket_bytes:
        return parse_ticket_uic_url(ticket_bytes, context)

    try:
        ber_tlv.tlv.Tlv.Parser.parse(ticket_bytes, False, [], False, 0)
        return parse_ticket_vdv(ticket_bytes, context)
    except Exception:
        pass

    if len(ticket_bytes) == 42:
        return parse_ticket_rsp_11(ticket_bytes)

    raise TicketError(
        title="This doesn't look like a ticket type we support.",
        message="If you'd like to see support for this added, please forward your original ticket to us.",
    )


def to_dict_json(elements: typing.List[typing.Tuple[str, typing.Any]]) -> dict:
    def encode_value(v):
        if isinstance(v, bytes) or isinstance(v, bytearray):
            return base64.b64encode(v).decode("ascii")
        elif isinstance(v, datetime.datetime) or isinstance(v, datetime.date):
            return v.isoformat()
        elif isinstance(v, enum.Enum):
            return v.value
        elif isinstance(v, dict):
            return {k: encode_value(i) for k, i in v.items()}
        elif isinstance(v, list):
            return [encode_value(i) for i in v]
        else:
            return v

    return {k: encode_value(v) for k, v in elements}


def create_ticket_obj(
        ticket_obj: "models.Ticket",
        ticket_bytes: bytes,
        ticket_data: typing.Union[
            VDVTicket, UICTicket, RSPTicket, SNCFTicket, ELBTicket, SSBTicket,
            SSB1Ticket, HZPPTicket, SwissPassTicket, IATATicket
        ],
) -> bool:
    created = False
    barcode_hash = hashlib.sha256(ticket_bytes).hexdigest()

    if isinstance(ticket_data, VDVTicket):
        _, created = models.VDVTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "ticket_org_id": ticket_data.ticket.ticket_org_id,
                "ticket_num": ticket_data.ticket.ticket_id,
                "validity_start": ticket_data.ticket.validity_start.as_datetime(),
                "validity_end": ticket_data.ticket.validity_end.as_datetime(),
                "barcode_data": ticket_bytes,
                "decoded_data": {
                    "root_ca": dataclasses.asdict(ticket_data.root_ca, dict_factory=to_dict_json),
                    "issuing_ca": dataclasses.asdict(ticket_data.issuing_ca, dict_factory=to_dict_json),
                    "envelope_certificate":
                        dataclasses.asdict(ticket_data.envelope_certificate, dict_factory=to_dict_json),
                    "ticket": base64.b64encode(ticket_data.raw_ticket).decode("ascii"),
                    "motics": dataclasses.asdict(ticket_data.motics,
                                                 dict_factory=to_dict_json) if ticket_data.motics else None,
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
        elif ticket_data.envelope:
            barcode_hash = hashlib.sha256(ticket_data.envelope.signed_data).hexdigest()
        else:
            barcode_hash = hashlib.sha256(ticket_data.raw_bytes).hexdigest()

        validity_start = None
        validity_end = None
        if ticket_data.flex:
            docs = ticket_data.flex.data.get("transportDocument")
            if docs:
                if docs[0]["ticket"][0] in ("openTicket", "pass"):
                    validity_start = templatetags.rics.rics_valid_from(docs[0]["ticket"][1],
                                                                       ticket_data.flex.issuing_time())
                    validity_end = templatetags.rics.rics_valid_until(docs[0]["ticket"][1],
                                                                      ticket_data.flex.issuing_time())
                elif docs[0]["ticket"][0] == "customerCard":
                    validity_start = templatetags.rics.rics_valid_from_date(docs[0]["ticket"][1])
                    validity_end = templatetags.rics.rics_valid_until_date(docs[0]["ticket"][1])
        elif ticket_data.st01:
            validity_start = datetime.datetime.combine(ticket_data.st01.valid_from,
                                                       datetime.time.min) if ticket_data.st01 else None
            validity_end = datetime.datetime.combine(ticket_data.st01.valid_to,
                                                     datetime.time.max) if ticket_data.st01 else None

        _, created = models.UICTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "distributor_rics": ticket_data.issuing_rics(),
                "ticket_pnr": ticket_data.ticket_id(),
                "issuing_time": ticket_data.issuing_time(),
                "barcode_data": ticket_bytes,
                "validity_start": validity_start,
                "validity_end": validity_end,
                "decoded_data": {
                    "envelope": dataclasses.asdict(ticket_data.envelope,
                                                   dict_factory=to_dict_json) if ticket_data.envelope else None,
                    "dosipas_envelope": dataclasses.asdict(ticket_data.dosipas_envelope,
                                                           dict_factory=to_dict_json) if ticket_data.dosipas_envelope else None,
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
    elif isinstance(ticket_data, FlexiTicket):
        _, created = models.FlexiTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            issuer_id=ticket_data.issuer_id,
            defaults={
                "ticket": ticket_obj,
                "barcode_data": ticket_bytes,
                "decoded_data": {
                    "raw_ticket": base64.b64encode(ticket_data.raw_ticket).decode(
                        "ascii") if ticket_data.raw_ticket else None,
                    "raw_extra_data": base64.b64encode(ticket_data.raw_extra_data).decode(
                        "ascii") if ticket_data.raw_extra_data else None,
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
    elif isinstance(ticket_data, HZPPTicket):
        _, created = models.HZPPTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "barcode_data": ticket_bytes,
            }
        )
    elif isinstance(ticket_data, SwissPassTicket):
        _, created = models.SwissPassTicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "barcode_data": ticket_bytes,
            }
        )
    elif isinstance(ticket_data, IATATicket):
        _, created = models.IATATicketInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "barcode_data": ticket_bytes,
            }
        )
    elif isinstance(ticket_data, BahnBonusCode):
        _, created = models.BahnBonusInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "barcode_data": ticket_bytes,
            }
        )
    elif isinstance(ticket_data, TS2Ticket):
        _, created = models.TS2Instance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "distributor_rics": ticket_data.envelope.issuer_rics,
                "barcode_data": ticket_bytes,
                "decoded_data": {
                    "envelope": dataclasses.asdict(ticket_data.envelope, dict_factory=to_dict_json),
                }
            }
        )
    elif isinstance(ticket_data, SNCBTrainPlus):
        _, created = models.SNCBTrainPlusInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "barcode_data": ticket_bytes,
            }
        )
    elif isinstance(ticket_data, ADIFTicket):
        _, created = models.ADIFInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "distributor_rics": ticket_data.issuer_id,
                "barcode_data": ticket_bytes,
            }
        )
    elif isinstance(ticket_data, MavTicket):
        _, created = models.MavInstance.objects.update_or_create(
            barcode_hash=barcode_hash,
            defaults={
                "ticket": ticket_obj,
                "distributor_rics": int(ticket_data.envelope.issuer_rics),
                "barcode_data": ticket_bytes,
                "decoded_data": {
                    "envelope": dataclasses.asdict(ticket_data.envelope, dict_factory=to_dict_json),
                }
            }
        )
    return created

def update_from_barcode(
        barcode_data: bytes, account: typing.Optional["models.Account"], force_update: bool = False
):
    decoded_ticket = parse_ticket(barcode_data, account=account)
    return update_from_ticket_object(decoded_ticket, barcode_data, account, force_update)


def update_from_ticket_object(
        decoded_ticket, barcode_data: bytes, account: typing.Optional["models.Account"], force_update: bool = False
) -> typing.Tuple["models.Ticket", bool]:
    should_update = force_update
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
        if not created:
            apn.notify_ticket.delay(ticket_obj.pk)
        gwallet.sync_ticket.delay(ticket_obj.pk)

    if created:
        email.send_new_ticket_email.delay(ticket_obj.pk)

    return ticket_obj, created
