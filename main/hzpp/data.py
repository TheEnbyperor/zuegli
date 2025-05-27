import dataclasses
import datetime
import decimal
import typing
import pytz
from Crypto.Cipher import AES
from django.conf import settings
from . import util


HZPP_EPOCH = pytz.timezone("Europe/Zagreb").localize(datetime.datetime(2003, 1, 1))


@dataclasses.dataclass
class Train:
    train_number: int
    reservation_reference: typing.Optional[str]
    seat: typing.Optional[str]

@dataclasses.dataclass
class JourneySegment:
    origin_station: int
    destination_station: int
    via_station: typing.Optional[int]
    travel_class: int
    train_type: int
    trains: typing.List[Train]

    def train_type_name(self):
        if self.train_type == 37:
            return "Regional"
        elif self.train_type == 102:
            return "InterCity"
        else:
            return f"Unknown ({self.train_type})"

@dataclasses.dataclass
class Passenger:
    passenger_type: int
    count: int

    def type_name(self):
        if self.passenger_type == 11:
            return "Adult"
        elif self.passenger_type == 12:
            return "Adult return"
        elif self.passenger_type == 13:
            return "Child"
        else:
            return f"Unknown ({self.passenger_type})"

@dataclasses.dataclass
class Customer:
    name: str
    address: str

@dataclasses.dataclass
class HZPPTicket:
    customer: typing.Optional[Customer]
    ticket_number: str
    ticket_type: int
    price: decimal.Decimal
    valid_from: datetime.datetime
    valid_until: datetime.datetime
    extended_validity: bool
    issued_on_board: bool
    passengers: typing.List[Passenger]
    journey_segments: typing.List[JourneySegment]

    @classmethod
    def parse(cls, data: bytes) -> "HZPPTicket":
        try:
            data = data.decode("iso-8859-1")
        except UnicodeDecodeError as e:
            raise util.HZPPException("Invalid ticket encoding") from e

        if data[:2] == "B1":
            return cls._parse_unencrypted(data[2:])
        elif data[:2] == "A1":
            return cls._parse_encrypted(data[2:])
        else:
            raise util.HZPPException("Not a HŽPP ticket")

    @classmethod
    def _parse_unencrypted(cls, data: str) -> "HZPPTicket":
        parts = data.split("|")

        if len(parts) != 33:
            raise util.HZPPException("Invalid number of ticket parts")

        try:
            ticket_number = parts[0]
            ticket_type_id =int(parts[1], 10)
            price = decimal.Decimal(int(parts[2], 10)) / decimal.Decimal(100)
            outbound_from_station = int(parts[3], 10)
            outbound_to_station = int(parts[4], 10)
            outbound_via_station = int(parts[5], 10)
            outbound_travel_class = int(parts[6], 10)
            outbound_train_type = int(parts[7], 10)
            return_from_station = int(parts[8], 10)
            return_to_station = int(parts[9], 10)
            return_via_station = int(parts[10], 10)
            return_travel_class = int(parts[11], 10)
            return_train_type = int(parts[12], 10)
            valid_from = HZPP_EPOCH + datetime.timedelta(minutes=int(parts[13], 10))
            valid_until = HZPP_EPOCH + datetime.timedelta(minutes=int(parts[14], 10))
            num_category_1_passengers = int(parts[15], 10)
            category_1_discount = int(parts[16], 10)
            num_category_2_passengers = int(parts[17], 10)
            category_2_discount = int(parts[18], 10)
            extended_validity = parts[19] == "1"
            issued_on_board = parts[20] == "1"
            outbound_train_1_number = int(parts[21], 10)
            outbound_train_1_reservation = parts[22]
            outbound_train_1_seats = parts[23]
            outbound_train_2_number = int(parts[24], 10)
            outbound_train_2_reservation = parts[25]
            outbound_train_2_seats = parts[26]
            return_train_1_number = int(parts[27], 10)
            return_train_1_reservation = parts[28]
            return_train_1_seats = parts[29]
            return_train_2_number = int(parts[30], 10)
            return_train_2_reservation = parts[31]
            return_train_2_seats = parts[32]
        except ValueError as e:
            raise util.HZPPException("Invalid data encoding") from e

        out = cls(
            customer=None,
            ticket_number=ticket_number,
            ticket_type=ticket_type_id,
            price=price,
            valid_from=valid_from,
            valid_until=valid_until,
            extended_validity=extended_validity,
            issued_on_board=issued_on_board,
            passengers=[],
            journey_segments=[],
        )

        if num_category_1_passengers:
            out.passengers.append(Passenger(
                passenger_type=category_1_discount,
                count=num_category_1_passengers,
            ))
        if num_category_2_passengers:
            out.passengers.append(Passenger(
                passenger_type=category_2_discount,
                count=num_category_2_passengers,
            ))

        if outbound_from_station or outbound_to_station:
            seg = JourneySegment(
                origin_station=outbound_from_station + 7800000,
                destination_station=outbound_to_station + 7800000,
                via_station=outbound_via_station + 7800000 if outbound_via_station else None,
                travel_class=outbound_travel_class,
                train_type=outbound_train_type,
                trains=[]
            )
            if outbound_train_1_number:
                seg.trains.append(Train(
                    train_number=outbound_train_1_number,
                    reservation_reference=outbound_train_1_reservation,
                    seat=outbound_train_1_seats,
                ))
            if outbound_train_2_number:
                seg.trains.append(Train(
                    train_number=outbound_train_2_number,
                    reservation_reference=outbound_train_2_reservation,
                    seat=outbound_train_2_seats,
                ))
            out.journey_segments.append(seg)

        if return_from_station or return_to_station:
            seg = JourneySegment(
                origin_station=return_from_station + 7800000,
                destination_station=return_to_station + 7800000,
                via_station=return_via_station + 7800000 if return_via_station else None,
                travel_class=return_travel_class,
                train_type=return_train_type,
                trains=[]
            )
            if return_train_1_number:
                seg.trains.append(Train(
                    train_number=return_train_1_number,
                    reservation_reference=return_train_1_reservation,
                    seat=return_train_1_seats,
                ))
            if return_train_2_number:
                seg.trains.append(Train(
                    train_number=return_train_2_number,
                    reservation_reference=return_train_2_reservation,
                    seat=return_train_2_seats,
                ))
            out.journey_segments.append(seg)

        return out

    @classmethod
    def _parse_encrypted(cls, data: str) -> "HZPPTicket":
        try:
            data = bytes.fromhex(data)
        except ValueError as e:
            raise util.HZPPException("Invalid ticket encoding") from e

        aes_iv = data[-16:]
        cipher = AES.new(settings.HZPP_KEY, AES.MODE_CBC, iv=aes_iv)
        data = cipher.decrypt(data[:-16])

        try:
            name = data[0:80].decode("windows-1250")
            address = data[80:160].decode("windows-1250")
            ticket_number = data[160:174].decode("ascii")
            ticket_type_id = int.from_bytes(data[174:178], "big")
            price = decimal.Decimal(int.from_bytes(data[178:182], "big")) / decimal.Decimal(100)
            outbound_from_station = int.from_bytes(data[182:185], "big")
            outbound_to_station = int.from_bytes(data[185:188], "big")
            outbound_via_station = int.from_bytes(data[188:191], "big")
            outbound_travel_class = data[191]
            outbound_train_type = data[192]
            return_from_station = int.from_bytes(data[193:196], "big")
            return_to_station = int.from_bytes(data[196:199], "big")
            return_via_station = int.from_bytes(data[199:202], "big")
            return_travel_class = data[202]
            return_train_type = data[203]
            valid_from = HZPP_EPOCH + datetime.timedelta(minutes=int.from_bytes(data[204:208], "big"))
            valid_until = HZPP_EPOCH + datetime.timedelta(minutes=int.from_bytes(data[208:212], "big"))
            num_category_1_passengers = data[212]
            category_1_discount = int.from_bytes(data[213:215], "big")
            num_category_2_passengers = data[215]
            category_2_discount = int.from_bytes(data[216:218], "big")
            extended_validity = data[218] == 1
            issued_on_board = data[219] == 1
            outbound_train_1_number = int.from_bytes(data[220:227], "big")
            outbound_train_1_reservation = data[227:257].decode("ascii")
            outbound_train_1_seats = data[257:317].decode("ascii")
            outbound_train_2_number = int.from_bytes(data[317:324], "big")
            outbound_train_2_reservation = data[324:354].decode("ascii")
            outbound_train_2_seats = data[354:414].decode("ascii")
            return_train_1_number = int.from_bytes(data[414:421], "big")
            return_train_1_reservation = data[421:451].decode("ascii")
            return_train_1_seats = data[451:511].decode("ascii")
            return_train_2_number = int.from_bytes(data[511:518], "big")
            return_train_2_reservation = data[518:548].decode("ascii")
            return_train_2_seats = data[548:608].decode("ascii")
        except ValueError as e:
            raise util.HZPPException("Invalid data encoding") from e

        out = cls(
            customer=Customer(
                name=name,
                address=address,
            ),
            ticket_number=ticket_number,
            ticket_type=ticket_type_id,
            price=price,
            valid_from=valid_from,
            valid_until=valid_until,
            extended_validity=extended_validity,
            issued_on_board=issued_on_board,
            passengers=[],
            journey_segments=[],
        )

        if num_category_1_passengers:
            out.passengers.append(Passenger(
                passenger_type=category_1_discount,
                count=num_category_1_passengers,
            ))
        if num_category_2_passengers:
            out.passengers.append(Passenger(
                passenger_type=category_2_discount,
                count=num_category_2_passengers,
            ))

        if outbound_from_station or outbound_to_station:
            seg = JourneySegment(
                origin_station=outbound_from_station + 7800000,
                destination_station=outbound_to_station + 7800000,
                via_station=outbound_via_station + 7800000 if outbound_via_station else None,
                travel_class=outbound_travel_class,
                train_type=outbound_train_type,
                trains=[]
            )
            if outbound_train_1_number:
                seg.trains.append(Train(
                    train_number=outbound_train_1_number,
                    reservation_reference=outbound_train_1_reservation,
                    seat=outbound_train_1_seats,
                ))
            if outbound_train_2_number:
                seg.trains.append(Train(
                    train_number=outbound_train_2_number,
                    reservation_reference=outbound_train_2_reservation,
                    seat=outbound_train_2_seats,
                ))
            out.journey_segments.append(seg)

        if return_from_station or return_to_station:
            seg = JourneySegment(
                origin_station=return_from_station + 7800000,
                destination_station=return_to_station + 7800000,
                via_station=return_via_station + 7800000 if return_via_station else None,
                travel_class=return_travel_class,
                train_type=return_train_type,
                trains=[]
            )
            if return_train_1_number:
                seg.trains.append(Train(
                    train_number=return_train_1_number,
                    reservation_reference=return_train_1_reservation,
                    seat=return_train_1_seats,
                ))
            if return_train_2_number:
                seg.trains.append(Train(
                    train_number=return_train_2_number,
                    reservation_reference=return_train_2_reservation,
                    seat=return_train_2_seats,
                ))
            out.journey_segments.append(seg)

        return out

    def price_str(self):
        if self.valid_from >= util.EURO_SWITCHOVER:
            return f"€{self.price:.2f}"
        else:
            return f"{self.price:.2f} HRK"
