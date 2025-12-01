import dataclasses
import gzip
import cryptography.exceptions
import cryptography.hazmat.primitives.hashes
from .util import MavException
from ..uic import certs

@dataclasses.dataclass
class Envelope:
    version: int
    signature_key_id: int
    ticket_id: str
    issuer_rics: int
    data: bytes
    signature: bytes

    def signing_cert(self):
        return certs.signing_cert(self.issuer_rics, str(self.signature_key_id))

    def can_verify(self):
        return bool(certs.public_key(self.issuer_rics, str(self.signature_key_id)))

    def verify_signature(self):
        pk = certs.public_key(self.issuer_rics, str(self.signature_key_id))
        if not pk:
            return False

        r, s = self.signature[0:28], self.signature[28:56]
        r = r.lstrip(b"\x00")
        s = s.lstrip(b"\x00")
        sig = bytearray([0x30, len(r) + len(s) + 4])
        if r[0] & 0x80:
            sig[1] += 1
            sig.extend([0x02, len(r) + 1, 0x00])
        else:
            sig.extend([0x02, len(r)])
        sig.extend(r)
        if s[0] & 0x80:
            sig[1] += 1
            sig.extend([0x02, len(s) + 1, 0x00])
        else:
            sig.extend([0x02, len(s)])
            sig.extend(s)
        sig = bytes(sig)

        hasher = cryptography.hazmat.primitives.hashes.SHA224()
        try:
            pk.verify(sig, self.data[:-56], hasher)
            return True
        except cryptography.exceptions.InvalidSignature:
            return False

    @classmethod
    def parse(cls, data: bytes) -> "Envelope":
        version = data[0]

        if version != 6:
            raise MavException(f"Unsupported version {version}")

        try:
            ticket_id = data[2:20].decode("ascii")
        except UnicodeDecodeError as e:
            raise MavException("Invalid ticket ID") from e

        try:
            issuer_rics = int(data[20:24].decode("ascii"), 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise MavException("Invalid issuer RICS") from e

        try:
            contents = gzip.decompress(data[24:-56])
        except (TypeError, ValueError) as e:
            raise MavException("Invalid ticket data") from e

        return cls(
            version=version,
            signature_key_id=data[1],
            ticket_id=ticket_id,
            issuer_rics=issuer_rics,
            data=contents,
            signature=data[-56:]
        )