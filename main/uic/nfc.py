import typing
import base64
import asn1tools
import urllib.parse
from django.conf import settings
from channels.generic.websocket import JsonWebsocketConsumer
from main import models, ticket
from . import dosipas, envelope, UICException


class Consumer(JsonWebsocketConsumer):
    account: typing.Optional[models.Account] = None

    def connect(self):
        qs = urllib.parse.parse_qs(self.scope["query_string"].decode("utf8"))

        if "account" in qs:
            account = models.Account.objects.filter(nfc_link_token=qs["account"][0]).first()
            if not account:
                self.close()
            self.account = account

        self.accept()

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
        self.close()

    def receive_json(self, message, **kwargs):
        if "type" not in message:
            self.error("Invalid message received")
            return

        message_type = message["type"]
        if message_type == "ndef":
            context = self.account.ticket_contexts() if self.account else ticket.TicketContexts([])
            tickets = []
            try:
                for record in message["ndef"]:
                    if record["tnf"] != "mime-type":
                        continue

                    mime_type = base64.b64decode(record["type"])
                    record_data = base64.b64decode(record["data"])

                    if mime_type == b"application/vnd.uic.dosipas.v2":
                        try:
                            data = dosipas.ASN1_SPEC_V2.decode("UicBarcodeHeader", record_data)
                            if data["format"] == "U2":
                                out = dosipas.DOSIPASEnvelope.from_decode(dosipas.DOSIPASEnvelope(
                                    version=2,
                                    level_2_data=data["level2SignedData"],
                                    level_2_signed_data=dosipas.ASN1_SPEC_V2.encode("Level2DataType", data["level2SignedData"]),
                                    level_2_signature=data.get("level2Signature"),
                                    level_1_signed_data=dosipas.ASN1_SPEC_V2.encode("Level1DataType", data["level2SignedData"]["level1Data"]),
                                    level_1_signature=data["level2SignedData"].get("level1Signature"),
                                    level_2_public_key=data["level2SignedData"]["level1Data"].get("level2PublicKey"),
                                ))
                                t = ticket.UICTicket.from_dosipas(record_data, out, context)
                                tickets.append((t, record_data))
                            else:
                                self.error("Tag contains invalid DOSIPAS")
                                return
                        except (asn1tools.DecodeError, IndexError):
                            self.error("Tag contains invalid DOSIPAS")
                            return
                    elif mime_type == b"application/vnd.uic.dosipas.v1":
                        try:
                            data = dosipas.ASN1_SPEC_V1.decode("UicBarcodeHeader", data)
                            if data["format"] == "U1":
                                out = dosipas.DOSIPASEnvelope.from_decode(dosipas.DOSIPASEnvelope(
                                    version=1,
                                    level_2_data=data["level2SignedData"],
                                    level_2_signed_data=dosipas.ASN1_SPEC_V1.encode("Level2DataType", data["level2SignedData"]),
                                    level_2_signature=data.get("level2Signature"),
                                    level_1_signed_data=dosipas.ASN1_SPEC_V1.encode("Level1DataType",data["level2SignedData"]["level1Data"]),
                                    level_1_signature=data["level2SignedData"].get("level1Signature"),
                                    level_2_public_key=data["level2SignedData"]["level1Data"].get("level2PublicKey"),
                                ))
                                t = ticket.UICTicket.from_dosipas(record_data, out, context)
                                tickets.append((t, record_data))
                            else:
                                self.error("Tag contains invalid DOSIPAS")
                                return
                        except (asn1tools.DecodeError, IndexError):
                            self.error("Tag contains invalid DOSIPAS")
                            return
                    elif mime_type == b"application/vnd.uic.tlb-fcb":
                        out = envelope.Envelope.parse(record_data)
                        t = ticket.UICTicket.from_envelope(record_data, out, context)
                        tickets.append((t, record_data))
            except UICException as e:
                self.error(f"Tag contains invalid ticket: {e}")
                return

            ticket_objs = []
            for (t, b) in tickets:
                ticket_objs.append(ticket.update_from_ticket_object(t, b, self.account, force_update=True)[0])

            if ticket_objs:
                self.done(f"{settings.EXTERNAL_URL_BASE}{ticket_objs[0].get_absolute_url()}")
            else:
                self.error("No usable records found")
        else:
            self.error("Unsupported message received")
