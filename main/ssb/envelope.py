import dataclasses
import typing
import cryptography.x509
import cryptography.exceptions
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.asymmetric.dsa
from . import util
from ..uic import rics, certs


@dataclasses.dataclass
class Envelope:
    version: int
    issuer_rics: int
    signature_key_id: int
    ticket_type: int
    data: util.BitStream
    signed_data: bytes
    signature: bytes

    def issuer(self):
        return rics.get_rics(self.issuer_rics)

    def signing_cert(self):
        return certs.signing_cert(self.issuer_rics, self.signature_key_id)

    def verify_signature(self):
        pk = certs.public_key(self.issuer_rics, self.signature_key_id)
        if not pk:
            return False

        if all(x == 0 for x in self.signature[-10:]):
            sig = bytearray([0x30, 0x2c])
            if self.signature[0] & 0x80:
                sig[1] += 1
                sig.extend([0x02, 0x15, 0x00])
            else:
                sig.extend([0x02, 0x14])
            sig.extend(self.signature[0:20])
            if self.signature[20] & 0x80:
                sig[1] += 1
                sig.extend([0x02, 0x15, 0x00])
            else:
                sig.extend([0x02, 0x14])
            sig.extend(self.signature[20:40])
            sig = bytes(sig)
            hasher = cryptography.hazmat.primitives.hashes.SHA1()
        else:
            sig = bytearray([0x30, 0x3c])
            if self.signature[0] & 0x80:
                sig[1] += 1
                sig.extend([0x02, 0x1d, 0x00])
            else:
                sig.extend([0x02, 0x1c])
            sig.extend(self.signature[0:28])
            if self.signature[28] & 0x80:
                sig[1] += 1
                sig.extend([0x02, 0x1d, 0x00])
            else:
                sig.extend([0x02, 0x1c])
            sig.extend(self.signature[28:56])
            sig = bytes(sig)
            hasher = cryptography.hazmat.primitives.hashes.SHA224()

        if isinstance(pk, cryptography.hazmat.primitives.asymmetric.dsa.DSAPublicKey):
            try:
                pk.verify(sig, self.signed_data, hasher)
                return True
            except cryptography.exceptions.InvalidSignature as e:
                print(f"Invalid signature {e}")
                return False
        else:
            return False

    @classmethod
    def parse(cls, data: bytes) -> "Envelope":
        if len(data) != 114:
            raise util.SSBException("Invalid length for an SSB barcode")

        d = util.BitStream(data[:58])

        version = d.read_int(0, 4)
        if version != 3:
            raise util.SSBException("Not an SSB barcode")

        return cls(
            version=version,
            issuer_rics=d.read_int(4, 18),
            signature_key_id=d.read_int(18, 22),
            ticket_type=d.read_int(22, 27),
            data=d[27:],
            signed_data=data[:58],
            signature=data[58:114]
        )