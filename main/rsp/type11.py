import dataclasses
import datetime
from . import util, data, issuers, locations


@dataclasses.dataclass
class Type11:
    barcode_type: str
    spec_version: int
    issuer_id: str
    ticket_ref: str
    ticket_type: str
    origin_nlc: str
    destination_nlc: str
    selling_nlc: str
    start_date: datetime.datetime
    standard_class: bool
    child_ticket: bool
    coupon_type: data.CouponType
    route_flag: str
    mandatory_manual_check: bool
    non_revenue: bool

    def issuer_name(self):
        return issuers.issuer_name(self.issuer_id)

    def validity_start_time(self):
        return data.TZ.localize(self.start_date)

    def validity_end_time(self):
        return data.TZ.localize(datetime.datetime.combine(self.start_date, datetime.time.max))

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

    @classmethod
    def parse(cls, payload: bytes) -> "Type11":
        if len(payload) != 42:
            raise util.RSPException("Not a type 11 barcode, wrong length")

        d = data.BitStream(payload)
        barcode_type = d.read_string7(0, 14)
        if barcode_type != "11":
            raise util.RSPException("Not a type 11 barcode, wrong type")

        version = d.read_string7(14, 28)
        issuer_id = d.read_string7(28, 42)
        ticket_ref = d.read_string7(42, 105)
        issuing_nlc = d.read_string7(105, 133)
        ticket_type = d.read_string7(133, 154)
        origin_nlc = d.read_string7(154, 182)
        destination_nlc = d.read_string7(182, 210)
        start_date = d.read_string7(210, 252)
        standard_class =  d.read_string7(252, 259)
        child_ticket =  d.read_string7(259, 266)
        coupon_type = d.read_string7(266, 273)
        route_flag = d.read_string7(273, 280)
        mandatory_manual_check = d.read_string7(280, 287)
        # bits 287-294 unused
        non_revenue_ticket = d.read_string7(294, 301)

        try:
            version = int(version)
        except ValueError:
            raise util.RSPException("Not a type 11 barcode, invalid version")

        try:
            start_date = datetime.datetime.strptime(str(start_date), "%d%m%y")
        except ValueError:
            raise util.RSPException("Not a type 11 barcode, invalid start date")

        try:
            coupon_type = int(coupon_type)
        except ValueError:
            raise util.RSPException("Not a type 11 barcode, invalid coupon type")

        return Type11(
            barcode_type=barcode_type,
            spec_version=version,
            issuer_id=issuer_id,
            ticket_ref=ticket_ref,
            ticket_type=ticket_type,
            selling_nlc=issuing_nlc,
            origin_nlc=origin_nlc,
            destination_nlc=destination_nlc,
            start_date=start_date,
            standard_class=standard_class == "1",
            child_ticket=child_ticket == "1",
            coupon_type=data.CouponType(coupon_type),
            route_flag=route_flag,
            mandatory_manual_check=mandatory_manual_check == "1",
            non_revenue=non_revenue_ticket == "1",
        )
