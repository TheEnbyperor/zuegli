import dataclasses
import enum
import datetime
import typing
from . import util

class PassengerType(enum.Enum):
    Adult = "0"
    Male = "1"
    Female = "2"
    Child = "3"
    Infant = "4"
    NonPassenger = "5"
    AdultWithInfant = "6"
    UnaccompaniedMinor = "7"
    Unknown = " "

    def __str__(self):
        if self == PassengerType.Adult:
            return "Adult"
        elif self == PassengerType.Male:
            return "Adult (male)"
        elif self == PassengerType.Female:
            return "Adult (female)"
        elif self == PassengerType.Child:
            return "Child"
        elif self == PassengerType.Infant:
            return "Infant"
        elif self == PassengerType.NonPassenger:
            return "Non-passenger e.g. luggage"
        elif self == PassengerType.AdultWithInfant:
            return "Adult with infant"
        elif self == PassengerType.UnaccompaniedMinor:
            return "Unaccompanied minor"
        elif self == PassengerType.Unknown:
            return "Unknown"

class CheckInSource(enum.Enum):
    Web = "W"
    AirportKiosk = "K"
    RemoteKiosk = "R"
    MobileDevice = "M"
    Agent = "O"
    TownAgent = "T"
    ThirdPartyVendor = "V"
    Unknown = " "

    def __str__(self):
        if self == CheckInSource.Web:
            return "Web"
        elif self == CheckInSource.AirportKiosk:
            return "Airport kiosk"
        elif self == CheckInSource.RemoteKiosk:
            return "Remote or off-site kiosk"
        elif self == CheckInSource.MobileDevice:
            return "Mobile device"
        elif self == CheckInSource.Agent:
            return "Airport agent"
        elif self == CheckInSource.TownAgent:
            return "Town agent"
        elif self == CheckInSource.ThirdPartyVendor:
            return "Third party vendor"
        elif self == CheckInSource.Unknown:
            return "Unknown"

class BoardingPassSource(enum.Enum):
    Web = "W"
    AirportKiosk = "K"
    TransferKiosk = "X"
    RemoteKiosk = "R"
    MobileDevice = "M"
    Agent = "O"
    TownAgent = "T"
    ThirdPartyVendor = "V"
    Unknown = " "

    def __str__(self):
        if self == BoardingPassSource.Web:
            return "Web"
        elif self == BoardingPassSource.AirportKiosk:
            return "Airport kiosk"
        elif self == BoardingPassSource.TransferKiosk:
            return "Transfer kiosk"
        elif self == BoardingPassSource.RemoteKiosk:
            return "Remote or off-site kiosk"
        elif self == BoardingPassSource.MobileDevice:
            return "Mobile device"
        elif self == BoardingPassSource.Agent:
            return "Airport agent"
        elif self == BoardingPassSource.TownAgent:
            return "Town agent"
        elif self == BoardingPassSource.ThirdPartyVendor:
            return "Third party vendor"
        elif self == BoardingPassSource.Unknown:
            return "Unknown"

class DocumentType(enum.Enum):
    BoardingPass = "B"
    ItineraryReceipt = "I"
    Unknown = " "

    def __str__(self):
        if self == DocumentType.BoardingPass:
            return "Boarding pass"
        elif self == DocumentType.ItineraryReceipt:
            return "Itinerary receipt"
        elif self == DocumentType.Unknown:
            return "Unknown"

class InternationalDocumentVerification(enum.Enum):
    NotRequired = "0"
    Required = "1"
    AlreadyPerformed = "2"
    Unknown = " "

    def __str__(self):
        if self == InternationalDocumentVerification.NotRequired:
            return "Not required"
        elif self == InternationalDocumentVerification.Required:
            return "Required - not yet performed"
        elif self == InternationalDocumentVerification.AlreadyPerformed:
            return "Already performed"
        elif self == InternationalDocumentVerification.Unknown:
            return "Unknown"


@dataclasses.dataclass
class UniqueConditional:
    version: str
    passenger_type: PassengerType
    check_in_source: CheckInSource
    boarding_pass_source: BoardingPassSource
    issue_date: typing.Optional[datetime.date]
    document_type: DocumentType
    issuer: str
    baggage_tags: typing.List[str]

    @classmethod
    def parse(cls, data: str) -> typing.Tuple["UniqueConditional", str]:
        if data[0] != ">":
            raise util.IATAException(f"Not an IATA conditional record, expected '>' found '{data[0]}'")

        version_number = data[1]
        try:
            structured_size = int(data[2:4], 16)
        except ValueError as e:
            raise util.IATAException("Invalid IATA structured data size") from e

        if len(data) + 4 < structured_size:
            raise util.IATAException("Not enough data")

        structured_data = data[4:4 + structured_size]
        second_structured_data = data[4 + structured_size:]

        if structured_data[3:7].strip():
            try:
                issue_year = int(structured_data[3])
                issue_day = int(structured_data[4:7])
            except ValueError as e:
                raise util.IATAException("Invalid IATA issue date") from e

            today = datetime.date.today()
            decade_start = (today.year // 10) * 10
            issue_date = datetime.date(decade_start + issue_year, 1, 1)
            issue_date += datetime.timedelta(days=issue_day - 1)

            if issue_date > today:
                issue_date = issue_date.replace(year=today.year - 10)
        else:
            issue_date = None

        offset = 11
        baggage_tags = []
        while len(structured_data) > offset:
            tag = structured_data[offset:offset + 13].rstrip()
            if tag:
                baggage_tags.append(tag)
            offset += 13

        return cls(
            version=version_number,
            passenger_type=PassengerType(structured_data[0] if len(structured_data) > 0 else " "),
            check_in_source=CheckInSource(structured_data[1] if len(structured_data) > 1 else " "),
            boarding_pass_source=BoardingPassSource(structured_data[2] if len(structured_data) > 2 else " "),
            issue_date=issue_date,
            document_type=DocumentType(structured_data[7] if len(structured_data) > 7 else " "),
            issuer=structured_data[8:11].rstrip(),
            baggage_tags=baggage_tags,
        ), second_structured_data


@dataclasses.dataclass
class LegConditional:
    airline_numeric_code: int
    document_serial: str
    selectee: typing.Optional[bool]
    international_document_verification: InternationalDocumentVerification
    marketing_carrier: str
    frequent_flyer_designator: str
    frequent_flyer_number: str
    industry_discount: str
    free_baggage_allowance: str
    fast_track: typing.Optional[bool]

    @classmethod
    def parse(cls, data: str) -> typing.Tuple[typing.Optional["LegConditional"], str]:
        if not data[:2].strip():
            return None, data

        try:
            structured_size = int(data[:2], 16)
        except ValueError as e:
            raise util.IATAException("Invalid IATA structured data size") from e

        data = data.ljust(2 + structured_size, " ")

        airline_data = data[2 + structured_size:]
        data = data[2:2 + structured_size]

        if data[0:3].strip():
            try:
                airline_numeric_code = int(data[0:3])
            except ValueError as e:
                raise util.IATAException("Invalid IATA airline number") from e
        else:
            airline_numeric_code = 0

        if data[13] == "1":
            selectee = True
        elif data[13] == "0":
            selectee = False
        elif data[13] == " ":
            selectee = None
        else:
            raise util.IATAException("Invalid selectee value")

        if structured_size >= 42:
            if data[41] == "Y":
                fast_track = True
            elif data[41] == "N":
                fast_track = False
            elif data[41] == " ":
                fast_track = None
            else:
                raise util.IATAException("Invalid fast track value")
        else:
            fast_track = None

        return cls(
            airline_numeric_code=airline_numeric_code,
            document_serial=data[3:13],
            selectee=selectee,
            international_document_verification=InternationalDocumentVerification(data[14]),
            marketing_carrier=data[15:18].rstrip(),
            frequent_flyer_designator=data[18:21].rstrip(),
            frequent_flyer_number=data[21:37].rstrip(),
            industry_discount=data[37].rstrip() if len(data) > 37 else "",
            free_baggage_allowance=data[38:41].rstrip() if len(data) > 41 else "",
            fast_track=fast_track,
        ), airline_data
