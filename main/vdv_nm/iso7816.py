import typing
import base64
import threading
import queue
import urllib.parse
from channels.generic.websocket import JsonWebsocketConsumer
from main import models

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

    def encode(self):
        if self.expected_response_length == 0:
            raise ValueError("Expected response length cannot be 0")

        out = bytearray([
            self.instruction_class,
            self.instruction,
            self.p1,
            self.p2,
        ])

        data_len = len(self.data)
        if data_len == 0:
            pass
        elif data_len < 256:
            out.append(data_len)
        elif data_len < 65536:
            out.append(0)
            out.extend(data_len.to_bytes(2, "big"))
        else:
            raise ValueError("Data length too long")
        out.extend(self.data)

        if self.expected_response_length == 0:
            pass
        else:
            if data_len >= 256:
                if self.expected_response_length == 65536:
                    out.append(0)
                    out.append(0)
                elif self.expected_response_length < 65536:
                    out.extend(self.expected_response_length.to_bytes(2, "big"))
                else:
                    raise ValueError("Invalid expected response length")
            else:
                if self.expected_response_length == 256:
                    out.append(0)
                elif self.expected_response_length == 65536:
                    out.append(0)
                    out.append(0)
                    out.append(0)
                elif self.expected_response_length < 256:
                    out.append(self.expected_response_length)
                elif self.expected_response_length < 65536:
                    out.append(0)
                    out.extend(self.expected_response_length.to_bytes(2, "big"))
                else:
                    raise ValueError("Invalid expected response length")
        return bytes(out)

class ResponseAPDU:
    sw1: int
    sw2: int
    data: bytes

    def __init__(self, sw1: int, sw2: int, data: bytes):
        self.sw1 = sw1
        self.sw2 = sw2
        self.data = data

    def __str__(self):
        return (f"ResponseAPDU(data={self.data.hex().upper()}, "
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


class Consumer(JsonWebsocketConsumer):
    current_aid: typing.Optional[str] = None
    identifier: typing.Optional[bytes] = None
    historical_bytes: typing.Optional[bytes] = None
    application_data: typing.Optional[bytes] = None
    transaction_queue: typing.Optional[queue.Queue] = None
    response: typing.Optional[ResponseAPDU] = None
    response_ready: threading.Event
    account: typing.Optional[models.Account] = None

    def acceptable_aids(self):
        raise NotImplementedError()

    def run(self):
        raise NotImplementedError()

    def connect(self):
        qs = urllib.parse.parse_qs(self.scope["query_string"].decode("utf8"))

        if "account" in qs:
            account = models.Account.objects.filter(nfc_link_token=qs["account"][0]).first()
            if not account:
                self.close()
            self.account = account

        self.transaction_queue = queue.Queue()
        self.response_ready = threading.Event()
        self.accept()
        t = threading.Thread(target=self.send_apdus, daemon=False)
        t.start()

    def disconnect(self, close_code):
        self.transaction_queue = None

    def send_apdus(self):
        while True:
            transaction = self.transaction_queue.get()
            if transaction is None:
                return
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
        self.transaction_queue.put(None)
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
        self.transaction_queue.put(None)
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
            if aid not in self.acceptable_aids():
                self.error("Unsupported AID")
                return

            self.identifier = base64.b64decode(message["identifier"])
            self.historical_bytes = base64.b64decode(message["historical-bytes"])
            self.application_data = base64.b64decode(message["application-data"])

            self.current_aid = message.get("aid", None)

            t = threading.Thread(target=self.run, daemon=False)
            t.start()
        elif message_type == "response-apdu":
            self.response = ResponseAPDU(
                sw1=message.get("sw1", 0),
                sw2=message.get("sw2", 0),
                data=base64.b64decode(message["data"]),
            )
            self.response_ready.set()
        elif message_type == "ndef":
            self.error("Unsupported tag type")

    def select_application_by_aid(self, aid: bytes):
        return self.apdu(RequestAPDU(
            instruction_class=0x00, instruction=0xA4, p1=0x04, p2=0x00,
            data=aid, expected_response_length=256
        ))
