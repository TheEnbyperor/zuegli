import dataclasses
import datetime
import google.protobuf.message
import pytz
import ber_tlv.tlv
from . import swisspass_pb2
from ..uic import rics

TZ = pytz.timezone('Europe/Zurich')

class SwissPassException(Exception):
    pass

@dataclasses.dataclass
class SwissPassTicket:
    ticket: swisspass_pb2.Ticket

    @classmethod
    def parse(cls, data: bytes) -> "SwissPassTicket":
        msg = swisspass_pb2.Ticket()
        try:
            msg.ParseFromString(data)
        except google.protobuf.message.DecodeError as e:
            raise SwissPassException("Not a valid Protobuf message") from e

        return cls(msg)

    def verify_signature(self):
        sig_data = ber_tlv.tlv.Tlv.parse(self.ticket.signature, True)
        sig = ber_tlv.tlv.Tlv.build(sig_data)

        return False

    def issuer(self):
        return rics.get_rics(self.ticket.signing_key.rics)

    @property
    def valid_from(self):
        return datetime.datetime.fromtimestamp(
            self.ticket.ticket_data.trip_data.valid_from.msecs / 1000,
            tz=TZ
        )

    @property
    def valid_until(self):
        return datetime.datetime.fromtimestamp(
            self.ticket.ticket_data.trip_data.valid_until.msecs / 1000,
            tz=TZ
        )

    @property
    def traveler_birthday(self):
        return datetime.datetime.fromtimestamp(
            self.ticket.ticket_data.traveler.birthday.msecs / 1000,
            tz=TZ
        )

    @property
    def issuing_time(self):
        return datetime.datetime.fromtimestamp(
            self.ticket.ticket_data.ticket_issue.issue_time.msecs / 1000,
            tz=TZ
        )

    @property
    def payment_method_name(self):
        if self.ticket.ticket_data.payment.payment_method == "MC":
            return "Mastercard"
        elif self.ticket.ticket_data.payment.payment_method == "VIS":
            return "Visa"
        elif self.ticket.ticket_data.payment.payment_method == "TWI":
            return "Twint"
        elif self.ticket.ticket_data.payment.payment_method == "PLU":
            return "Halbtax Plus"
        elif self.ticket.ticket_data.payment.payment_method == "PCD":
            return "Postcard Debit"
        else:
            return f"Unknown - {self.ticket.ticket_data.payment.payment_method}"
