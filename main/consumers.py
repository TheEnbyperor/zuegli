import typing
import base64
import threading
import queue
from channels.generic.websocket import JsonWebsocketConsumer

ACCEPTABLE_AIDS = [
    "D2760001354B414E4D303100"
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

class Transaction:
    request: RequestAPDU
    response: typing.Optional[ResponseAPDU] = None
    response_ready: threading.Event

    def __init__(self, request: RequestAPDU):
        self.request = request
        self.response_ready = threading.Event()

class VDVConsumer(JsonWebsocketConsumer):
    current_aid: typing.Optional[str] = None
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

    def done(self):
        self.send_json({
            "type": "done",
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
            if aid not in ACCEPTABLE_AIDS:
                self.error("Unsupported AID")
                return

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
        fci = self.apdu(RequestAPDU(
            instruction_class=0x00, instruction=0xA4, p1=0x04, p2=0x00,
            data=bytes.fromhex("D2760001354B414E4D303100"), expected_response_length=256
        ))
        print(fci)

        application_directory = self.apdu(RequestAPDU(
            instruction_class=0x00, instruction=0xA4, p1=0x04, p2=0x0C,
            data=bytes.fromhex("D2760001354B414E4D303100"), expected_response_length=256
        ))
        print(application_directory)

        application_pk = self.apdu(RequestAPDU(
            instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0x11,
            data=b"", expected_response_length=256
        ))
        print(application_pk)

        ca_pk = self.apdu(RequestAPDU(
            instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0x12,
            data=b"", expected_response_length=256
        ))
        print(ca_pk)

        self.done()
