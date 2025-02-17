import dataclasses
import datetime
import enum
import typing
from . import util, conditional

class Compartment(enum.Enum):
    Supersonic = "R"
    PremiumFirst = "P"
    First = "F"
    DiscountedFirst = "A"
    PremiumBusiness = "J"
    Business = "C"
    DiscountedBusinessD = "D"
    DiscountedBusinessI = "I"
    DiscountedBusinessZ = "Z"
    PremiumEconomy = "W"
    Economy = "Y"
    DiscountedEconomyB = "B"
    DiscountedEconomyH = "H"
    DiscountedEconomyK = "K"
    DiscountedEconomyL = "L"
    DiscountedEconomyM = "M"
    DiscountedEconomyN = "N"
    DiscountedEconomyQ = "Q"
    DiscountedEconomyT = "T"
    DiscountedEconomyV = "V"
    DiscountedEconomyX = "X"
    Unknown = " "

    def __str__(self):
        if self == Compartment.Supersonic:
            return "Supersonic"
        elif self == Compartment.PremiumFirst:
            return "First class - premium"
        elif self == Compartment.First:
            return "First class - full fare"
        elif self == Compartment.DiscountedFirst:
            return "First class - discounted"
        elif self == Compartment.PremiumBusiness:
            return "Business class - premium"
        elif self == Compartment.Business:
            return "Business class - full fare"
        elif self == Compartment.DiscountedBusinessD:
            return "Business class - discounted (D)"
        elif self == Compartment.DiscountedBusinessI:
            return "Business class - discounted (I)"
        elif self == Compartment.DiscountedBusinessZ:
            return "Business class - discounted (Z)"
        elif self == Compartment.PremiumEconomy:
            return "Economy class - premium"
        elif self == Compartment.Economy:
            return "Economy class - full fare"
        elif self == Compartment.DiscountedEconomyB:
            return "Economy class - discounted (B)"
        elif self == Compartment.DiscountedEconomyH:
            return "Economy class - discounted (H)"
        elif self == Compartment.DiscountedEconomyK:
            return "Economy class - discounted (K)"
        elif self == Compartment.DiscountedEconomyL:
            return "Economy class - discounted (L)"
        elif self == Compartment.DiscountedEconomyM:
            return "Economy class - discounted (M)"
        elif self == Compartment.DiscountedEconomyN:
            return "Economy class - discounted (N)"
        elif self == Compartment.DiscountedEconomyQ:
            return "Economy class - discounted (Q)"
        elif self == Compartment.DiscountedEconomyT:
            return "Economy class - discounted (T)"
        elif self == Compartment.DiscountedEconomyV:
            return "Economy class - discounted (V)"
        elif self == Compartment.DiscountedEconomyX:
            return "Economy class - discounted (X)"
        elif self == Compartment.Unknown:
            return "Unknown"

class PassengerStatus(enum.Enum):
    NotCheckedIn = "0"
    CheckedIn = "1"
    BaggageCheckedPassengerNotCheckedIn = "2"
    BaggageCheckedPassengerCheckedIn = "3"
    PassengerPassedSecurity = "4"
    PassengerPassedGateExit = "5"
    Transit = "6"
    Standby = "7"
    Revalidation = "8"
    OriginalBoardingLineUsed = "9"

    def __str__(self):
        if self == PassengerStatus.NotCheckedIn:
            return "Not checked in"
        elif self == PassengerStatus.CheckedIn:
            return "Checked in"
        elif self == PassengerStatus.BaggageCheckedPassengerNotCheckedIn:
            return "Baggage checked - passenger not checked in"
        elif self == PassengerStatus.BaggageCheckedPassengerCheckedIn:
            return "Baggage checked - passenger checked in"
        elif self == PassengerStatus.PassengerPassedSecurity:
            return "Passenger passed security"
        elif self == PassengerStatus.PassengerPassedGateExit:
            return "Passenger passed gate exit"
        elif self == PassengerStatus.Transit:
            return "Transit"
        elif self == PassengerStatus.Standby:
            return "Standby"
        elif self == PassengerStatus.Revalidation:
            return "Revalidation done"
        elif self == PassengerStatus.OriginalBoardingLineUsed:
            return "Original boarding line used"


@dataclasses.dataclass
class Leg:
    pnr: str
    from_code: str
    to_code: str
    operating_carrier: str
    flight_number: str
    date: typing.Optional[datetime.date]
    compartment: Compartment
    seat: str
    sequence: str
    passenger_status: PassengerStatus
    conditional: typing.Optional[conditional.LegConditional]
    airline_data: typing.Optional[str]

    @classmethod
    def parse(cls, data: str) -> "Leg":
        if len(data) < 35:
            raise util.IATAException("IATA data too short")

        try:
            date_num = int(data[21:24])
        except ValueError as e:
            raise util.IATAException("Invalid date") from e

        if date_num != 0:
            date = datetime.date.today().replace(day=1, month=1)
            date += datetime.timedelta(days=date_num - 1)
        else:
            date = None

        return cls(
            pnr=data[0:7].rstrip(),
            from_code=data[7:10],
            to_code=data[10:13],
            operating_carrier=data[13:16].rstrip(),
            flight_number=data[16:21].rstrip().lstrip("0"),
            date=date,
            compartment=Compartment(data[24:25]),
            seat=data[25:29].lstrip("0"),
            sequence=data[29:34].rstrip().lstrip("0"),
            passenger_status=PassengerStatus(data[34]),
            conditional=None,
            airline_data=None,
        )
