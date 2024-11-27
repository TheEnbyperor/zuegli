import dataclasses
import base26
import hashlib
import typing
from . import util, pki, issuers


@dataclasses.dataclass
class Envelope:
    ticket_type: str
    issuer_id: str
    ticket_ref: str
    payload: bytes

    def issuer_name(self):
        return issuers.issuer_name(self.issuer_id)

    @classmethod
    def parse(cls, d: bytes) -> "Envelope":
        if len(d) < 16:
            raise util.RSPException("Envelope is too short")

        if d[0:2] not in (b"06", b"08"):
            raise util.RSPException("Envelope isn't an RSP ticket")

        try:
            ticket_ref = d[2:11].decode()
            issuer_id = d[13:15].decode()
        except UnicodeDecodeError as e:
            raise util.RSPException("Invalid ticket reference encoding") from e

        try:
            payload = base26.decode(d[15:].decode())
        except UnicodeDecodeError as e:
            raise util.RSPException("Invalid payload encoding") from e

        return cls(
            ticket_type=d[0:2].decode(),
            issuer_id=issuer_id,
            ticket_ref=ticket_ref,
            payload=payload,
        )

    def decrypt_with_cert(self, cert: pki.Certificate) -> typing.Optional[bytes]:
        h = int.from_bytes(self.payload, 'big')
        m = pow(h, cert.exponent, cert.modulus)
        data = m.to_bytes(cert.modulus_len, 'big')

        if data[0] == 0 and data[1] == 1:
            offset = 2
            while data[offset] == 0xFF:
                offset += 1
            if data[offset] == 0:
                data = data[offset+1:]
            else:
                return None
        else:
            return None

        data, message_hash = data[:-8], data[-8:]

        if hashlib.sha256(data).digest()[:8] != message_hash:
            raise util.RSPException("Invalid message integrity hash")

        return data