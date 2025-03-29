import typing
import base64
import threading
import queue
import datetime
import Crypto.Hash.TupleHash128
from channels.generic.websocket import JsonWebsocketConsumer
from django.conf import settings
from . import vdv_nm
from . import vdv
from . import models


ACCEPTABLE_AIDS = [
    vdv_nm.util.VDV_KA_NM_AID
]

class RequestAPDU:
    instruction_class: int
    instruction: int
    p1: int
    p2: int
    data: bytes
    expected_response_length: int

    def __init__(
            self, instruction_class: int, instruction: int, p1: int, p2: int,
            data: bytes, expected_response_length: int
    ):
        self.instruction_class = instruction_class
        self.instruction = instruction
        self.p1 = p1
        self.p2 = p2
        self.data = data
        self.expected_response_length = expected_response_length

    def __str__(self):
        return (f"RequestAPDU(class={self.instruction_class:02x}, "
                f"instruction={self.instruction:02x}, "
                f"p1={self.p1:02x}, p2={self.p2:02x}, "
                f"data={self.data.hex().upper()}), "
                f"expected_response_length={self.expected_response_length})")

    def __repr__(self):
        return str(self)

class ResponseAPDU:
    sw1: int
    sw2: int
    data: bytes

    def __init__(self, sw1: int, sw2: int, data: bytes):
        self.sw1 = sw1
        self.sw2 = sw2
        self.data = data

    def __str__(self):
        return (f"ResponseAPDU(data={self.data.hex().upper()}), "
                f"sw1={self.sw1:02x}, sw2={self.sw2:02x})")

    def __repr__(self):
        return str(self)

    def is_success(self):
        return self.sw1 == 0x90 and self.sw2 == 0x00


class Transaction:
    request: RequestAPDU
    response: typing.Optional[ResponseAPDU] = None
    response_ready: threading.Event

    def __init__(self, request: RequestAPDU):
        self.request = request
        self.response_ready = threading.Event()

class VDVConsumer(JsonWebsocketConsumer):
    current_aid: typing.Optional[str] = None
    identifier: typing.Optional[bytes] = None
    historical_bytes: typing.Optional[bytes] = None
    application_data: typing.Optional[bytes] = None
    transaction_queue: typing.Optional[queue.Queue] = None
    response: typing.Optional[ResponseAPDU] = None
    response_ready: threading.Event

    def connect(self):
        self.transaction_queue = queue.Queue()
        self.response_ready = threading.Event()
        self.accept()
        t = threading.Thread(target=self.send_apdus, daemon=False)
        t.start()

    def disconnect(self, close_code):
        self.transaction_queue = None

    def send_apdus(self):
        while self.transaction_queue:
            transaction = self.transaction_queue.get()
            self.send_json({
                "type": "request-apdu",
                "class": transaction.request.instruction_class,
                "instruction": transaction.request.instruction,
                "p1": transaction.request.p1,
                "p2": transaction.request.p2,
                "data": base64.b64encode(transaction.request.data).decode("ascii"),
                "expected-response-length": transaction.request.expected_response_length,
            })
            self.response_ready.wait()
            transaction.response = self.response
            self.response = None
            transaction.response_ready.set()
            self.response_ready.clear()

    def error(self, message: str):
        self.send_json({
            "type": "error",
            "message": message
        })
        self.close()

    def message(self, message: str):
        self.send_json({
            "type": "message",
            "message": message
        })

    def done(self, return_url: str):
        self.send_json({
            "type": "done",
            "return-url": return_url
        })
        self.transaction_queue = None
        self.close()

    def apdu(self, request: RequestAPDU) -> ResponseAPDU:
        transaction = Transaction(request)
        self.transaction_queue.put(transaction)
        transaction.response_ready.wait()
        return transaction.response

    def receive_json(self, message, **kwargs):
        if "type" not in message:
            self.error("Invalid message received")
            return

        message_type = message["type"]
        if message_type == "connected":
            if self.current_aid is not None:
                self.error("Multiple connections")
                return

            aid = message.get("aid", None)
            if not aid:
                self.error("Invalid message received")
                return
            try:
                aid = bytes.fromhex(aid)
            except ValueError:
                self.error("Invalid message received")
                return
            if aid not in ACCEPTABLE_AIDS:
                self.error("Unsupported AID")
                return

            self.identifier = base64.b64decode(message["identifier"])
            self.historical_bytes = base64.b64decode(message["historical-bytes"])
            self.application_data = base64.b64decode(message["application-data"])

            self.current_aid = message.get("aid", None)
            self.message("Reading card...")

            t = threading.Thread(target=self.run, daemon=False)
            t.start()
        elif message_type == "response-apdu":
            self.response = ResponseAPDU(
                sw1=message.get("sw1", 0),
                sw2=message.get("sw2", 0),
                data=base64.b64decode(message["data"]),
            )
            self.response_ready.set()

    def run(self):
        try:
            fci_data = self.apdu(RequestAPDU(
                instruction_class=0x00, instruction=0xA4, p1=0x04, p2=0x00,
                data=vdv_nm.util.VDV_KA_NM_AID, expected_response_length=256,
            ))
            if not fci_data.is_success():
                self.error("Failed to read File Control Information")
                return

            vdv_nm.fci.FCI.parse(fci_data.data)

            application_directory_data = self.apdu(RequestAPDU(
                instruction_class=0x00, instruction=0xA4, p1=0x04, p2=0x0C,
                data=vdv_nm.util.VDV_KA_NM_AID, expected_response_length=256,
            ))
            if not application_directory_data.is_success():
                self.error("Failed to read Application Directory")
                return

            application_directory = vdv_nm.application_directory.ApplicationDirectory.parse(application_directory_data.data)

            hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)
            hd.update(b"vdv-ka-nm")
            hd.update(application_directory.application_data.application_instance_org_id.to_bytes(8, "big"))
            hd.update(application_directory.application_data.application_instance_number.to_bytes(8, "big"))
            card_id = base64.b32hexencode(hd.digest()).decode("utf-8")

            application_data = self.apdu(RequestAPDU(
                instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0xF0,
                data=bytes([0xEE, application_directory.application_data.data_pointer]),
                expected_response_length=256,
            ))
            if not application_data.is_success():
                self.error("Failed to read Application Data")
                return

            ca_pk_data = self.apdu(RequestAPDU(
                instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0x12,
                data=b"", expected_response_length=65536,
            ))
            if not ca_pk_data.is_success():
                self.error("Failed to read CA Certificate")

            ca_pk = vdv.Certificate.parse(ca_pk_data.data)
            vdv.CertificateData.parse(ca_pk)

            application_pk_data = self.apdu(RequestAPDU(
                instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0x11,
                data=b"", expected_response_length=65536,
            ))
            if not application_pk_data.is_success():
                self.error("Failed to read Application Certificate")
                return

            application_pk = vdv.Certificate.parse(application_pk_data.data)
            vdv.CertificateData.parse(application_pk)

            card, _ = models.VDVSmartcard.objects.update_or_create(
                id=card_id,
                defaults={
                    "atr_identifier": self.identifier,
                    "atr_historical_bytes": self.historical_bytes,
                    "atr_application_data": self.application_data,
                    "last_updated": datetime.datetime.now(),
                    "fci": fci_data.data,
                    "application_directory": application_directory_data.data,
                    "ca_cert": ca_pk_data.data,
                    "application_cert": application_pk_data.data,
                }
            )
            self.done(f"{settings.EXTERNAL_URL_BASE}{card.get_absolute_url()}")
        except (vdv_nm.VDVNMException, vdv.VDVException) as e:
            self.error(str(e))
