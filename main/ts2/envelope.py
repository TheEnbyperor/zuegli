import dataclasses
import typing
import ber_tlv.tlv
import cryptography.x509
import cryptography.exceptions
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.asymmetric.dsa
import zlib

from ..uic import rics, certs
from . import util

@dataclasses.dataclass
class Envelope:
    version: int
    issuer_rics: int
    signature_key_id: typing.Union[int, str]
    data: bytes
    signature: bytes = None
    signed_data: bytes = None

    def issuer(self):
        return rics.get_rics(self.issuer_rics)

    def signing_cert(self):
        return certs.signing_cert(self.issuer_rics, self.signature_key_id)

    def can_verify(self):
        return bool(certs.public_key(self.issuer_rics, self.signature_key_id))

    def revoked_key(self):
        return self.issuer_rics == 5211 and self.signature_key_id == 1

    def verify_signature(self):
        if not self.signature or not self.signed_data:
            return False

        pk = certs.public_key(self.issuer_rics, self.signature_key_id)
        if not pk:
            return False

        meta, _ = certs.signing_cert(self.issuer_rics, self.signature_key_id)

        sig_data = ber_tlv.tlv.Tlv.parse(self.signature, True)
        sig = ber_tlv.tlv.Tlv.build(sig_data)
        if meta:
            if meta["signature_algorithm"] == "SHA224withDSA":
                hasher = cryptography.hazmat.primitives.hashes.SHA224()
            else:
                hasher = cryptography.hazmat.primitives.hashes.SHA256()
        else:
            hasher = cryptography.hazmat.primitives.hashes.SHA256()

        if isinstance(pk, cryptography.hazmat.primitives.asymmetric.dsa.DSAPublicKey):
            try:
                pk.verify(sig, self.signed_data, hasher)
                return True
            except cryptography.exceptions.InvalidSignature:
                return False
        else:
            return False

    @classmethod
    def parse(cls, data: bytes) -> "Envelope":
        if data[:3] != b"TS2":
            raise util.TS2Exception("Invalid TS2 ticket magic")

        if len(data) < 88:
            raise util.TS2Exception("TS2 ticket too short")

        try:
            version_str = data[3:5].decode("ascii")
            version = int(version_str, 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise util.TS2Exception("Invalid TS2 ticket version") from e

        if version != 2:
            raise util.TS2Exception("Unsupported TS2 ticket version")

        try:
            provider_str = data[5:9].decode("ascii")
            provider = int(provider_str, 10)
            signature_key_id_str = data[9:14].decode("ascii")
        except (UnicodeDecodeError, ValueError) as e:
            raise util.TS2Exception("Invalid TS2 ticket provider or signature key ID") from e

        try:
            signature_key_id = int(signature_key_id_str, 10)
        except ValueError:
            signature_key_id = signature_key_id_str

        signature, data = data[14:88], data[88:]

        try:
            data_length_str = data[0:4].decode("ascii")
            data_length = int(data_length_str, 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise util.TS2Exception("Invalid TS2 ticket data length") from e

        if len(data) < 4 + data_length:
            raise util.TS2Exception("TS2 ticket data too short")

        signed_data = data[4:]

        try:
            raw_ticket = zlib.decompress(data[4:4+data_length])
        except zlib.error as e:
            raise util.TS2Exception("Failed to decompress UIC ticket data") from e

        return cls(
            version=version,
            issuer_rics=provider,
            signature_key_id=signature_key_id,
            signature=signature,
            signed_data=signed_data,
            data=raw_ticket,
        )
