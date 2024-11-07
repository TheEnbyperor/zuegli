import dataclasses
import enum
import typing
import ber_tlv.tlv
import re
from . import util, org_id, product_id

NAME_TYPE_1_RE = re.compile(r"(?P<start>\w?)(?P<len>\d+)(?P<end>\w?)")


@dataclasses.dataclass
class Context:
    account_forename: typing.Optional[str]
    account_surname: typing.Optional[str]


@dataclasses.dataclass
class VDVTicket:
    version: str
    ticket_id: int
    ticket_org_id: int
    product_number: int
    product_org_id: int
    validity_start: util.DateTime
    validity_end: util.DateTime
    kvp_org_id: int
    terminal_type: int
    terminal_number: int
    terminal_owner_id: int
    transaction_time: util.DateTime
    location_type: int
    location_number: int
    location_org_id: int
    sam_sequence_number_1: int
    sam_sequence_number_2: int
    sam_version: int
    sam_id: int
    product_data: typing.List["ELEMENT"]
    product_transaction_data: bytes

    def __str__(self):
        out = "VDVTicket:\n" \
              f"""  Version: {self.version}\n""" \
              f"""  Ticket:\n""" \
              f"""    ID: {self.ticket_id}\n""" \
              f"""    Organization ID: {self.ticket_org_id}\n""" \
              f"""  Product:\n""" \
              f"""    Number: {self.product_number}\n""" \
              f"""    Organization ID: {self.product_org_id}\n""" \
              f"""  Validity:\n""" \
              f"""   Start: {self.validity_start}\n""" \
              f"""   End: {self.validity_end}\n""" \
              f"""  Transaction:\n""" \
              f"""    Time: {self.transaction_time}\n""" \
              f"""    KVP Organization ID: {self.kvp_org_id}\n""" \
              f"""    Terminal:\n""" \
              f"""      Type: {self.terminal_type}\n""" \
              f"""      Number: {self.terminal_number}\n""" \
              f"""      Owner ID: {self.terminal_owner_id}\n""" \
              f"""    Location:\n""" \
              f"""      Type: {self.location_type}\n""" \
              f"""      Number: {self.location_number}\n""" \
              f"""      Organization ID: {self.location_org_id}\n""" \
              f"""  SAM:\n""" \
              f"""    Sequence Number 1: {self.sam_sequence_number_1}\n""" \
              f"""    Sequence Number 2: {self.sam_sequence_number_2}\n""" \
              f"""    Version: {self.sam_version}\n""" \
              f"""    ID: {self.sam_id}\n""" \
              f"""  Product Data:"""
        if not self.product_data:
            out += " N/A"
        else:
            for d in self.product_data:
                out += f"""\n    {d}"""
        out += "\n  Product Transaction Data:"
        if not self.product_transaction_data:
            out += " N/A"
        else:
            for d in self.product_transaction_data:
                out += f"""\n    {d}"""
        return out

    @classmethod
    def parse(cls, data: bytes, context: Context) -> "VDVTicket":
        if len(data) < 111:
            raise util.VDVException("Invalid VDV ticket length")

        header, data = data[0:18], data[18:]

        try:
            parser = ber_tlv.tlv.Tlv.Parser(data, [], 0)
            product_data = parser.next()
        except Exception as e:
            raise util.VDVException("Invalid VDV ticket") from e

        if product_data[0] != 0x85:
            raise util.VDVException("Not a VDV ticket")

        product_data = ber_tlv.tlv.Tlv.parse(product_data[1], False, False)

        offset_1 = parser.get_offset()
        common_transaction_data, data = data[offset_1:offset_1 + 17], data[offset_1 + 17:]

        try:
            parser = ber_tlv.tlv.Tlv.Parser(data, [], 0)
            product_transaction_data = parser.next()
        except Exception as e:
            raise util.VDVException("Invalid VDV ticket") from e

        if product_transaction_data[0] != 0x8A:
            raise util.VDVException("Not a VDV ticket")

        offset_2 = parser.get_offset()
        ticket_issue_data, data = data[offset_2:offset_2 + 12], data[offset_2 + 12:]

        trailer = data[-5:]

        if trailer[0:3] != b'VDV':
            raise util.VDVException("Not a VDV ticket")

        version = f"{trailer[3] >> 4}.{trailer[3] & 0x0F}.{trailer[4]:02d}"

        return cls(
            version=version,
            ticket_id=int.from_bytes(header[0:4], 'big'),
            ticket_org_id=int.from_bytes(header[4:6], 'big'),
            product_number=int.from_bytes(header[6:8], 'big'),
            product_org_id=int.from_bytes(header[8:10], 'big'),
            validity_start=util.DateTime.from_bytes(header[10:14]),
            validity_end=util.DateTime.from_bytes(header[14:18]),
            kvp_org_id=int.from_bytes(common_transaction_data[0:2], 'big'),
            terminal_type=common_transaction_data[2],
            terminal_number=int.from_bytes(common_transaction_data[3:5], 'big'),
            terminal_owner_id=int.from_bytes(common_transaction_data[5:7], 'big'),
            transaction_time=util.DateTime.from_bytes(common_transaction_data[7:11]),
            location_type=common_transaction_data[11],
            location_number=int.from_bytes(common_transaction_data[12:15], 'big'),
            location_org_id=int.from_bytes(common_transaction_data[15:17], 'big'),
            sam_sequence_number_1=int.from_bytes(ticket_issue_data[0:4], 'big'),
            sam_version=ticket_issue_data[4],
            sam_sequence_number_2=int.from_bytes(ticket_issue_data[5:9], 'big'),
            sam_id=int.from_bytes(ticket_issue_data[9:12], 'big'),
            product_data=list(map(lambda e: cls.parse_product_data_element(e, context), product_data)),
            product_transaction_data=product_transaction_data[1]
        )

    @staticmethod
    def parse_product_data_element(elm, context: Context) -> typing.Any:
        if elm[0] == 0xDB:
            return PassengerData.parse(elm[1], context)
        elif elm[0] == 0xDA:
            return BasicData.parse(elm[1])
        elif elm[0] == 0xE0:
            return IdentificationMedium.parse(elm[1])
        elif elm[0] == 0xDC:
            return SpacialValidity.parse(elm[1])
        else:
            return UnknownElement(elm[0], elm[1])

    def product_name(self, opt=False):
        if self.product_number == 9999:
            return "Deutschlandticket"
        elif self.product_number == 9998:
            return "Deutschlandjobticket"
        elif self.product_number == 9997:
            return "Startkarte Deutschlandticket"
        elif self.product_number == 9996:
            return "Deutschlandsemesterticket"
        elif self.product_number == 9995:
            return "Deutschlandschülerticket"
        else:
            product_id_map = product_id.get_product_id_list()
            if name := product_id_map.get((self.product_org_id, self.product_number)):
                return name
            else:
                if opt:
                    return None
                return f"{self.product_org_name()}:{self.product_number}"

    def product_name_opt(self):
        return self.product_name(True)

    def product_org_name(self):
        return map_org_id(self.product_org_id)

    def product_org_name_opt(self):
        return map_org_id(self.product_org_id, True)

    def ticket_org_name(self):
        return map_org_id(self.ticket_org_id)

    def ticket_org_name_opt(self):
        return map_org_id(self.ticket_org_id, True)

    def kvp_org_name(self):
        return map_org_id(self.kvp_org_id)

    def kvp_org_name_opt(self):
        return map_org_id(self.kvp_org_id, True)

    def terminal_type_name(self, opt=False):
        if self.terminal_type == 0:
            return "Unbestimmt"
        elif self.terminal_type == 1:
            return "Erfassungsterminal für CICO/BIBO"
        elif self.terminal_type == 2:
            return "Verkaufsautomat (z. B. Berechtigungen)"
        elif self.terminal_type == 3:
            return "Kontrollterminal (mobil, personalbedient)"
        elif self.terminal_type == 4:
            return "Kartenausgabeterminal"
        elif self.terminal_type == 5:
            return "Kartenrückgabeterminal Einstiegskontrollgerät"
        elif self.terminal_type == 6:
            return "Entwerter"
        elif self.terminal_type == 7:
            return "Multifunktionsterminal (kundenbedient)"
        elif self.terminal_type == 8:
            return "Informationsterminal Ladeterminal"
        elif self.terminal_type == 9:
            return "für ÖPV-Werteinheiten"
        elif self.terminal_type == 13:
            return "Terminal beim Massenpersonalisierer 13"
        elif self.terminal_type == 14:
            return "Servicestelle (personalbedient)"
        elif self.terminal_type == 15:
            return "Fahrerterminal (Verkauf und Kontrolle)"
        elif self.terminal_type == 16:
            return "HandyTicketserver"
        elif self.terminal_type == 17:
            return "eOnline Ticketserver"
        elif self.terminal_type == 18:
            return "Verkaufsautomat mobil (kundenbedient)"
        elif self.terminal_type == 19:
            return "Kontrollterminalmobil (personalbedient)"
        else:
            if opt:
                return None
            return f"Unknown ({self.terminal_type})"

    def terminal_type_name_opt(self):
        return self.terminal_type_name(True)

    def terminal_owner_name(self):
        return map_org_id(self.terminal_owner_id)

    def terminal_owner_name_opt(self):
        return map_org_id(self.terminal_owner_id, True)

    def location_type_name(self, opt=False):
        if self.location_type == 0:
            return "Bushaltestelle"
        elif self.location_type == 1:
            return "U-Bahn- (Metro-)Station"
        elif self.location_type == 2:
            return "Bahnhof (Eisenbahn)"
        elif self.location_type == 3:
            return "Straßenbahn- (TRAM-) Haltestelle"
        elif self.location_type == 11:
            return "Verkaufsstelle"
        elif self.location_type == 16:
            return "Gebiet (auch für Zone)"
        elif self.location_type == 17:
            return "Korridor"
        elif self.location_type == 200:
            return "Haltestelle allgemein für Haltestellen im Fahrplansinne, unabhängig vom Verkehrsmittel"
        elif self.location_type == 201:
            return "Massenpersonalisierer"
        elif self.location_type == 202:
            return "areaList_ID"
        elif self.location_type == 203:
            return "im Fahrzeug/Zug"
        elif self.location_type == 204:
            return "TouchPoint"
        elif self.location_type == 205:
            return "im Fahrzeug der Linie"
        elif self.location_type == 206:
            return "im Fahrzeug der Zugnummer"
        elif self.location_type == 207:
            return "Teilzone"
        elif self.location_type == 208:
            return "neutrale Zone"
        elif self.location_type == 213:
            return "im Fahrzeug an Haltestelle"
        elif self.location_type == 214:
            return "Ereignisort"
        elif self.location_type == 215:
            return "Ticketserver"
        elif self.location_type == 251:
            return "Ortsteil"
        elif self.location_type == 252:
            return "Gemeinde (Gemeindekennziffer)"
        elif self.location_type == 253:
            return "Kreis"
        elif self.location_type == 254:
            return "Land"
        elif self.location_type == 255:
            return "keine Angabe"
        else:
            if opt:
                return None
            return f"Unknown ({self.terminal_type})"

    def location_type_name_opt(self):
        return self.location_type_name(True)

    def location_org_name(self):
        return map_org_id(self.location_org_id)

    def location_org_name_opt(self):
        return map_org_id(self.location_org_id, True)

@dataclasses.dataclass
class BasicData:
    TYPE = "basic-data"

    payment_type: int
    passenger_type: int
    first_additional_travelers: typing.Optional["Mitnahme"]
    second_additional_travelers: typing.Optional["Mitnahme"]
    transport_category: int
    service_class: int
    price_base: str
    vat_rate: int
    price_level: int
    internal_product_number: int

    @classmethod
    def parse(cls, data: bytes) -> "BasicData":
        return cls(
            payment_type=data[0],
            passenger_type=data[1],
            first_additional_travelers=Mitnahme(data[2], data[3]) if data[2] else None,
            second_additional_travelers=Mitnahme(data[4], data[5]) if data[4] else None,
            transport_category=data[6],
            service_class=data[7],
            price_base=f"{int.from_bytes(data[8:11]) / 100:.2f}",
            vat_rate=int.from_bytes(data[11:13]),
            price_level=data[13],
            internal_product_number=int.from_bytes(data[14:17], "big"),
        )

    def payment_type_name_opt(self):
        if self.payment_type == 0:
            return None
        elif self.payment_type == 1:
            return "Bar"
        elif self.payment_type == 2:
            return "Kreditkarte"
        elif self.payment_type == 3:
            return "POB/PEB"
        elif self.payment_type == 6:
            return "EC-Karte / Lastschrift"
        elif self.payment_type == 7:
            return "Rechnung"
        elif self.payment_type == 8:
            return "Werteinheiten"
        elif self.payment_type == 14:
            return "Gutschein"
        elif self.payment_type == 17:
            return "ECcash"
        elif self.payment_type == 24:
            return "GeldKarte"
        elif self.payment_type == 25:
            return "Mastercard"
        elif self.payment_type == 26:
            return "Visa"
        elif self.payment_type == 27:
            return "HandyTicket Konto"
        elif self.payment_type == 28:
            return "Mobilfunkrechnung"
        else:
            return None

    @staticmethod
    def map_passenger_type(t: int):
        if t == 0:
            return None
        elif t == 1:
            return "Erwachsener"
        elif t == 2:
            return "Kind"
        elif t == 3:
            return "Student"
        elif t == 5:
            return "Behinderter nicht weiter spezifiziert"
        elif t == 6:
            return "Sehbehinderter"
        elif t == 7:
            return "Hörgeschädigter"
        elif t == 8:
            return "Arbeitsloser/Sozialhilfeempfänger"
        elif t == 9:
            return "Personal"
        elif t == 10:
            return "Militärangehöriger"
        elif t == 17:
            return "Kostenpflichtiges Tier"
        elif t == 19:
            return "Schüler"
        elif t == 20:
            return "Azubi"
        elif t == 25:
            return "Senior"
        elif t == 64:
            return "Ermäßigt"
        elif t == 65:
            return "Fahrrad"
        elif t == 66:
            return "Hund"

    def passenger_type_name_opt(self):
        return self.map_passenger_type(self.passenger_type)

    def service_class_name(self):
        if self.service_class == 1:
            return "1. Klasse"
        elif self.service_class == 2:
            return "2. Klasse"
        else:
            return f"Unknown ({self.service_class})"

@dataclasses.dataclass
class Mitnahme:
    passenger_type: int
    passenger_count: int

    def __init__(self, t: int, c: int):
        self.passenger_type = t
        self.passenger_count = c

    def passenger_type_name_opt(self):
        return BasicData.map_passenger_type(self.passenger_type)

@dataclasses.dataclass
class IdentificationMedium:
    TYPE = "identification-medium"

    id_type: int
    id_number: str

    @classmethod
    def parse(cls, data: bytes) -> "IdentificationMedium":
        return cls(
            id_type=data[0],
            id_number=data[1:].decode("iso-8859-15", "replace"),
        )

    def type_name_opt(self):
        if self.id_type == 69:
            return "Girocard der deutschen Kreditwirtschaft (EC-Karte)"
        elif self.id_type == 75:
            return "Kreditkarte"
        elif self.id_type == 80:
            return "Personalausweis"
        elif self.id_type == 84:
            return "Telefonnummer"
        elif self.id_type == 90:
            return "Sozialpass"
        elif self.id_type == 83:
            return "Schüler-/Studentenausweis"
        else:
            return None


class Gender(enum.Enum):
    Unspecified = 0
    Male = 1
    Female = 2
    Diverse = 3


@dataclasses.dataclass
class PassengerData:
    TYPE = "passenger-data"

    gender: Gender
    date_of_birth: typing.Optional[util.Date]
    forename: str
    original_forename: typing.Optional[str]
    surname: str
    original_surname: typing.Optional[str]

    def __str__(self):
        return f"Passenger: forename={self.forename}, surname={self.surname}, date_of_birth={self.date_of_birth}, gender={self.gender}"

    @classmethod
    def parse(cls, data: bytes, context: Context) -> "PassengerData":
        if len(data) < 5:
            raise util.VDVException("Invalid passenger data element")

        name = data[5:].decode("iso-8859-15", "replace")
        forename = ""
        original_forename = None
        original_surname = None
        if "#" in name:
            forename, surname = name.split("#", 1)
            if context.account_forename and context.account_forename.startswith(forename):
                forename = context.account_forename
            if context.account_surname and context.account_surname.startswith(surname):
                surname = context.account_surname
        elif "@" in name:
            forename, surname = name.split("@", 1)
            new_forename = []
            new_surname = []
            while forename_match := NAME_TYPE_1_RE.match(forename):
                forename = forename[forename_match.end():]
                forename_start = forename_match.group("start")
                forename_end = forename_match.group("end")
                forename_len = int(forename_match.group("len"))
                new_forename.append(f"{forename_start}{'_' * forename_len}{forename_end}")

            while surname_match := NAME_TYPE_1_RE.match(surname):
                surname = surname[surname_match.end():]
                surname_start = surname_match.group("start")
                surname_end = surname_match.group("end")
                surname_len = int(surname_match.group("len"))
                new_surname.append(f"{surname_start}{'_' * surname_len}{surname_end}")

            if new_forename:
                forename = " ".join(new_forename)
                if context.account_forename and len(context.account_forename) == len(forename):
                    if (
                            context.account_forename.startswith(forename[0]) and
                            context.account_forename.endswith(forename[-1])
                    ) or (
                            (context.account_forename.startswith(forename[0]) or
                             context.account_forename.endswith(forename[-1])) and
                            len(forename) == 2
                    ) or (
                            len(forename) == 1
                    ):
                        original_forename = forename
                        forename = context.account_forename

            if new_surname:
                surname = " ".join(new_surname)
                if context.account_surname and len(context.account_surname) == len(surname):
                    if (
                            context.account_surname.startswith(surname[0]) and
                            context.account_surname.endswith(surname[-1])
                    ) or (
                            (context.account_surname.startswith(surname[0]) or
                             context.account_surname.endswith(surname[-1])) and
                            len(surname) == 2
                    ) or (
                            len(surname) == 1
                    ):
                        original_surname = surname
                        surname = context.account_surname
        else:
            surname = name

        return cls(
            gender=Gender(data[0]),
            date_of_birth=util.Date.from_bytes(data[1:5]) if all(d != 0 for d in data[1:5]) else None,
            forename=forename,
            surname=surname,
            original_forename=original_forename,
            original_surname=original_surname
        )


@dataclasses.dataclass
class SpacialValidity:
    TYPE = "spacial-validity"

    definition_type: int
    organization_id: int
    area_ids: typing.List[int]

    def __str__(self):
        return f"Spacial validity: org_id={self.organization_id}, area_ids={','.join(map(str, self.area_ids))}"

    @classmethod
    def parse(cls, data: bytes):
        if data[0] in (0x0F, 0x10):
            return cls(
                definition_type=data[0],
                organization_id=int.from_bytes(data[1:3], 'big'),
                area_ids=[int.from_bytes(data[i:i + 2], 'big') for i in range(3, len(data), 2)]
            )
        else:
            return UnknownSpacialValidity(
                definition_type=data[0],
                value=data[1:]
            )

    def organization_name(self):
        return map_org_id(self.organization_id)

    def organization_name_opt(self):
        return map_org_id(self.organization_id, True)


@dataclasses.dataclass
class UnknownSpacialValidity:
    TYPE = "unknown-spacial-validity"

    definition_type: int
    value: bytes

    def __str__(self):
        return f"Unknown spacial validity: type=0x{self.definition_type:02X}, value={self.value.hex()}"

    def type_hex(self):
        return f"0x{self.definition_type:02X}"

    def data_hex(self):
        return ":".join(f"{self.value[i]:02x}" for i in range(len(self.value)))


@dataclasses.dataclass
class UnknownElement:
    TYPE = "unknown"

    tag: int
    value: bytes

    def __str__(self):
        return f"Unknown element 0x{self.tag:02X}: {self.value.hex()}"

    def tag_hex(self):
        return f"0x{self.tag:02X}"

    def data_hex(self):
        return ":".join(f"{self.value[i]:02x}" for i in range(len(self.value)))


ELEMENT = typing.Union[
    BasicData, PassengerData, SpacialValidity, IdentificationMedium,
    UnknownSpacialValidity, UnknownElement
]

def map_org_id(code: int, opt=False):
    org, is_test = org_id.get_org(code)
    if org:
        if is_test:
            return f"{org['name']} (Test)"
        else:
            return org['name']
    if opt:
        return ""
    else:
        return str(org_id)
