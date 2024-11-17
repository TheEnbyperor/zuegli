import dataclasses
import datetime
import bitstring
import pytz
from main.rsp import RSPException
from . import locations

TZ = pytz.timezone("Europe/London")


class BitStream:
    data: bitstring.ConstBitStream

    def __init__(self, data: bytes):
        self.data = bitstring.ConstBitStream(data)

    def read_bool(self, index: int) -> bool:
        return bool(self.data[index])

    def read_bytes(self, start: int, end: int) -> bytes:
        return self.data[start:end].bytes

    def read_string(self, start: int, end: int) -> str:
        out = bytearray()
        for i in range(start, end, 6):
            out.append(self.data[i:i+6].uint + 0x20)

        return out.decode("ascii").strip()

    def read_int(self, start: int, end: int) -> int:
        return self.data[start:end].uint

    def read_date(self, start: int, end: int) -> datetime.date:
        i = self.read_int(start, end)
        return datetime.date(1997, 1, 1) + datetime.timedelta(days=i)

    def read_time(self, start: int, end: int) -> datetime.time:
        i = self.read_int(start, end)
        return datetime.time((i // 3600) % 24, (i // 60) % 60, i % 60)

@dataclasses.dataclass
class TicketData:
    mandatory_manual_check: bool

    @classmethod
    def parse(cls, payload: bytes):
        d = BitStream(payload)

        return cls(
            mandatory_manual_check=d.read_bool(0),
        )

@dataclasses.dataclass
class RailcardData:
    mandatory_manual_check: bool
    non_revenue: bool
    spec_version: int
    issuer_id: str
    ticket_reference: str
    checksum: str
    barcode_version: int
    start_date: datetime.date
    end_date: datetime.date
    passenger_1_title: str
    passenger_1_forename: str
    passenger_1_surname: str
    passenger_2_title: str
    passenger_2_forename: str
    passenger_2_surname: str
    purchase_date: datetime.datetime
    railcard_type: str
    railcard_number: str
    selling_machine_type: int
    selling_nlc: str
    selling_machine_number: int
    selling_transaction_number: int
    no_ipe: bool
    free_use: str
    sha256_hash: bytes

    @classmethod
    def parse(cls, payload: bytes):
        if len(payload) != 116:
            raise RSPException(f"Invalid length for railcard data - expected 116 bytes, got {len(payload)} bytes")

        d = BitStream(payload)

        return cls(
            mandatory_manual_check=d.read_bool(0),
            non_revenue=d.read_bool(1),
            spec_version=d.read_int(2, 4),
            issuer_id=d.read_string(4, 16),
            ticket_reference=d.read_string(16, 70),
            checksum=d.read_string(70, 76),
            barcode_version=d.read_int(76, 80),
            start_date=d.read_date(80, 94),
            end_date=d.read_date(94, 108),
            passenger_1_title=d.read_string(108, 132),
            passenger_1_forename=d.read_string(132, 222),
            passenger_1_surname=d.read_string(222, 312),
            passenger_2_title=d.read_string(312, 336),
            passenger_2_forename=d.read_string(336, 426),
            passenger_2_surname=d.read_string(426, 516),
            purchase_date=datetime.datetime.combine(d.read_date(516, 530), d.read_time(530, 541)),
            # 25 bits - RFU
            railcard_type=d.read_string(566, 584),
            railcard_number=d.read_string(584, 680),
            selling_machine_type=d.read_int(680, 687),
            selling_nlc=d.read_string(687, 711),
            selling_machine_number=d.read_int(711, 725),
            selling_transaction_number=d.read_int(725, 742),
            no_ipe=d.read_bool(742),
            # 1 bit - RFU
            free_use=d.read_string(744, 864),
            sha256_hash=d.read_bytes(864, 928)
        )

    def has_passenger_2(self):
        return bool(self.passenger_2_title or self.passenger_2_forename or self.passenger_2_surname)

    def sha256_hash_hex(self):
        return ":".join(f"{b:02x}" for b in self.sha256_hash)

    def passenger_1_name(self):
        return f"{self.passenger_1_title + ' ' if self.passenger_1_title else ''}{self.passenger_1_forename} {self.passenger_1_surname}"

    def passenger_2_name(self):
        return f"{self.passenger_2_title + ' ' if self.passenger_2_title else ''}{self.passenger_2_forename} {self.passenger_2_surname}"

    def validity_start_time(self):
        return TZ.localize(datetime.datetime.combine(self.start_date, datetime.time.min))

    def validity_end_time(self):
        return TZ.localize(datetime.datetime.combine(self.end_date, datetime.time.max))

    def purchase_time(self):
        return TZ.localize(self.purchase_date)

    def issuer_name(self):
        if self.issuer_id == "TT":
            return "Trainline"
        elif self.issuer_id == "R5":
            return "Raileasy"
        else:
            return f"Unknown - {self.issuer_id}"

    def railcard_type_name(self):
        if self.railcard_type == "TSU":
            return "16-17 Saver"
        elif self.railcard_type == "YNG":
            return "16-25 Railcard"
        elif self.railcard_type == "TST":
            return "26-30 Railcard"
        elif self.railcard_type == "SRN":
            return "Senior Railcard"
        elif self.railcard_type == "FAM":
            return "Family & Friends Railcard"
        elif self.railcard_type == "DIS":
            return "Disabled Persons Railcard"
        elif self.railcard_type == "HMF":
            return "HM Forces Railcard"
        elif self.railcard_type == "VET":
            return "Veterans Railcard"
        elif self.railcard_type == "NEW":
            return "Network Railcard"
        elif self.railcard_type == "NGC":
            return "Gold Card"
        elif self.railcard_type == "2TR":
            return "Two Together Railcard"
        elif self.railcard_type == "CRC":
            return "Cambrian Railcard"
        elif self.railcard_type == "CTD":
            return "Cotswold Railcard"
        elif self.railcard_type == "DRD":
            return "Dales Railcard"
        elif self.railcard_type == "DCR":
            return "Devon & Cornwall Railcard"
        elif self.railcard_type == "EVC":
            return "Esk Valley Railcard"
        elif self.railcard_type == "HOW":
            return "Heart of Wales Railcard"
        elif self.railcard_type == "HRC":
            return "Highlands Railcard"
        elif self.railcard_type == "IRC":
            return "Island Resident Card"
        elif self.railcard_type == "PBR":
            return "Pembrokeshire Railcard"
        elif self.railcard_type == "JCP":
            return "Jobcentre Plus Travel Discount Card"
        else:
            return "Unknown Railcard Type"
        
    def background_colour(self):
        if self.railcard_type == "2TR":
            return "#6e1f7e"
        elif self.railcard_type == "YNG":
            return "#e97201"
        elif self.railcard_type == "TST":
            return "#e32706"
        elif self.railcard_type == "FAM":
            return "#df202a"
        elif self.railcard_type == "SRN":
            return "#180a56"
        elif self.railcard_type == "DIS":
            return "#01835d"
        elif self.railcard_type == "NEW":
            return "#1075cf"

    def selling_nlc_name(self):
        if l := locations.get_station_by_nlc(self.selling_nlc):
            return l["NLCDESC"]

        return "Unknown location"