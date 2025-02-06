import dataclasses
import datetime
import enum

import bitstring
import pytz
import typing
import decimal
from . import locations, util, issuers

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
        return datetime.time((i // 60) % 24, i % 60, 0)

@dataclasses.dataclass
class PurchaseData:
    purchase_date: datetime.datetime
    price: decimal.Decimal
    discounted: bool
    restriction: str
    purchase_reference: str
    days_of_validity: int
    additional_adults: int
    additional_children: int

    def purchase_time(self):
        return TZ.localize(self.purchase_date)

    def price_str(self):
        return f"£{self.price:.2f}"

@dataclasses.dataclass
class Reservation:
    service_id: str
    coach: str
    seat: str

class CouponType(enum.Enum):
    Single = 0
    Season = 1
    Outbound = 2
    Inbound = 3

    def __str__(self):
        if self == CouponType.Single:
            return "Single"
        elif self == CouponType.Season:
            return "Season"
        elif self == CouponType.Outbound:
            return "Return - outbound"
        elif self == CouponType.Inbound:
            return "Return - inbound"

class DepartureTime(enum.Enum):
    NotSet = 0
    ValidAfter = 1
    SpecificDeparture = 2

    def __str__(self):
        if self == DepartureTime.NotSet:
            return "time not specified"
        elif self == DepartureTime.ValidAfter:
            return "valid after"
        elif self == DepartureTime.SpecificDeparture:
            return "specific departure"

@dataclasses.dataclass
class TicketData:
    mandatory_manual_check: bool
    multiple_supplements_apply: bool
    on_paper: bool
    static_dynamic_indicator: int
    non_revenue: bool
    spec_version: int
    ticket_reference: str
    checksum: str
    barcode_version: int
    standard_class: bool
    lennon_ticket_type: str
    fare_label: str
    origin_nlc: str
    destination_nlc: str
    selling_nlc: str
    child_ticket: bool
    coupon_type: CouponType
    discount_code: int
    route_code: int
    start_date: datetime.datetime
    depart_time: DepartureTime
    passenger_id: int
    parent_ticket_reference: str
    passenger_gender: int
    restriction_code: str
    via_london: bool
    osi_nlc: str
    bidirectional: bool
    carnet_count: int
    limited_duration_code: int
    sub_utn: bool
    print_free_use: bool
    purchase_data: typing.Optional[PurchaseData]
    reservations: typing.List[Reservation]
    free_use: str

    def version_name(self):
        if self.spec_version == 2:
            return "2.0"
        elif self.spec_version == 3:
            return "2.1"
        elif self.spec_version == 0:
            return "2.2"
        elif self.spec_version == 1:
            return "2.3"

    @classmethod
    def parse(cls, payload: bytes):
        d = BitStream(payload)

        if len(payload) < 108:
            raise util.RSPException(f"Invalid length for ticket data - expected 108 bytes, got {len(payload)} bytes")

        has_optional_data = d.read_bool(384)
        num_reservations = d.read_int(386, 390)

        offset = 390
        reservations = []

        if has_optional_data:
            purchase_data = PurchaseData(
                purchase_date=datetime.datetime.combine(d.read_date(offset, offset+14), d.read_time(offset+14, offset+25)),
                price=decimal.Decimal(d.read_int(offset+25, offset+46)) / decimal.Decimal(100),
                discounted=d.read_bool(offset+46),
                restriction=d.read_string(offset+47, offset+59),
                purchase_reference=d.read_string(offset+59, offset+107),
                days_of_validity=d.read_int(offset+107, offset+116),
                additional_adults=d.read_int(offset+116, offset+119),
                additional_children=d.read_int(offset+119, offset+122),
            )
            offset += 122
        else:
            purchase_data = None

        for _ in range(num_reservations):
            service_id_1 = d.read_string(offset, offset+12)
            service_id_2 = d.read_int(offset+12, offset+26)
            seat_1 = d.read_string(offset+32, offset+38)
            seat_2 = d.read_int(offset+38, offset+45)
            reservations.append(Reservation(
                service_id=f"{service_id_1}{service_id_2}",
                coach=d.read_string(offset+26, offset+32),
                seat=f"{seat_2}{seat_1}" if seat_2 else "",
            ))
            offset += 45

        free_use = d.read_string(offset, offset+172)

        return cls(
            mandatory_manual_check=d.read_bool(0),
            multiple_supplements_apply=d.read_bool(1),
            on_paper=d.read_bool(2),
            static_dynamic_indicator=d.read_int(3, 5),
            non_revenue=d.read_bool(5),
            spec_version=d.read_int(6, 8),
            ticket_reference=d.read_string(8, 62),
            checksum=d.read_string(62, 68),
            barcode_version=d.read_int(68, 72),
            standard_class=d.read_bool(72),
            lennon_ticket_type=d.read_string(73, 91),
            fare_label=d.read_string(91, 109),
            origin_nlc=d.read_string(109, 133).lstrip(" 0"),
            destination_nlc=d.read_string(133, 157).lstrip(" 0"),
            selling_nlc=d.read_string(157, 181).lstrip(" 0"),
            child_ticket=d.read_bool(181),
            coupon_type=CouponType(d.read_int(182, 184)),
            discount_code=d.read_int(184, 194),
            route_code=d.read_int(194, 211),
            start_date=datetime.datetime.combine(d.read_date(211, 225), d.read_time(225, 236)),
            depart_time=DepartureTime(d.read_int(236, 238)),
            passenger_id=d.read_int(238, 255),
            parent_ticket_reference=d.read_string(255, 327),
            passenger_gender=d.read_int(327, 329),
            restriction_code=d.read_string(329, 347),
            via_london=d.read_bool(347),
            osi_nlc=d.read_string(348, 372),
            bidirectional=d.read_bool(372),
            carnet_count=d.read_int(373, 379),
            limited_duration_code=d.read_int(379, 383),
            sub_utn=d.read_bool(383),
            # 384 read above
            print_free_use=d.read_bool(385),
            # 386-390 read above
            purchase_data=purchase_data,
            reservations=reservations,
            free_use=free_use
        )

    def limited_duration_value(self):
        if self.limited_duration_code == 1:
            return datetime.timedelta(minutes=15)
        elif self.limited_duration_code == 2:
            return datetime.timedelta(minutes=30)
        elif self.limited_duration_code == 3:
            return datetime.timedelta(minutes=45)
        elif self.limited_duration_code == 4:
            return datetime.timedelta(hours=1)
        elif self.limited_duration_code == 5:
            return datetime.timedelta(minutes=90)
        elif self.limited_duration_code == 6:
            return datetime.timedelta(hours=2)
        elif self.limited_duration_code == 7:
            return datetime.timedelta(hours=3)
        elif self.limited_duration_code == 8:
            return datetime.timedelta(hours=4)
        elif self.limited_duration_code == 9:
            return datetime.timedelta(hours=5)
        elif self.limited_duration_code == 10:
            return datetime.timedelta(hours=6)
        elif self.limited_duration_code == 11:
            return datetime.timedelta(hours=8)
        elif self.limited_duration_code == 12:
            return datetime.timedelta(hours=10)
        elif self.limited_duration_code == 13:
            return datetime.timedelta(hours=12)
        elif self.limited_duration_code == 14:
            return datetime.timedelta(hours=18)
        else:
            return None

    def validity_start_time(self):
        return TZ.localize(self.start_date)

    def validity_end_time(self):
        limited_duration = self.limited_duration_value()
        if limited_duration:
            return TZ.localize(self.start_date + limited_duration)

        if self.purchase_data:
            base = self.validity_start_time() + datetime.timedelta(days=max(self.purchase_data.days_of_validity - 1, 0))
        else:
            base = self.validity_start_time()
        return TZ.localize(datetime.datetime.combine(base.date(), datetime.time.max))

    def origin_nlc_name(self):
        if l := locations.get_station_by_nlc(self.origin_nlc):
            return l["NLCDESC"]

        return "Unknown location"

    def destination_nlc_name(self):
        if l := locations.get_station_by_nlc(self.destination_nlc):
            return l["NLCDESC"]

        return "Unknown location"

    def selling_nlc_name(self):
        if l := locations.get_station_by_nlc(self.selling_nlc):
            return l["NLCDESC"]

        return "Unknown location"

    def osi_nlc_name(self):
        if l := locations.get_station_by_nlc(self.osi_nlc):
            return l["NLCDESC"]

        return "Unknown location"

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

    @classmethod
    def parse(cls, payload: bytes):
        if len(payload) < 108:
            raise util.RSPException(f"Invalid length for railcard data - expected 108 bytes, got {len(payload)} bytes")

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
            selling_nlc=d.read_string(687, 711).lstrip(" 0"),
            selling_machine_number=d.read_int(711, 725),
            selling_transaction_number=d.read_int(725, 742),
            no_ipe=d.read_bool(742),
            # 1 bit - RFU
            free_use=d.read_string(744, 864),
        )

    def has_passenger_2(self):
        return bool(self.passenger_2_title or self.passenger_2_forename or self.passenger_2_surname)

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
        return issuers.issuer_name(self.issuer_id)

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