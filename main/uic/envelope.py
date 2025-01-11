import dataclasses
import typing
import ber_tlv.tlv
import cryptography.x509
import cryptography.exceptions
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.asymmetric.dsa
import zlib

from . import util, rics, certs


@dataclasses.dataclass
class Record:
    id: str
    version: int
    data: bytes
    is_utf8_len: bool = False

    def data_hex(self):
        return ":".join(f"{b:02x}" for b in self.data)

    @classmethod
    def parse(cls, data: bytes) -> "Record":
        if len(data) < 12:
            raise util.UICException("UIC ticket record too short")

        try:
            record_id = data[0:6].decode("ascii")
        except UnicodeDecodeError as e:
            raise util.UICException("Invalid UIC ticket record ID") from e

        try:
            version_str = data[6:8].decode("ascii")
            version = int(version_str, 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise util.UICException("Invalid UIC ticket record version") from e

        try:
            data_length_str = data[8:12].decode("ascii")
            data_length = int(data_length_str, 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise util.UICException("Invalid UIC ticket record data length") from e

        is_utf8_len = False
        data_utf8 = data[12:].decode("utf8", "replace")[:data_length]
        if len(data) < data_length:
            if len(data_utf8) + 12 < data_length:
                raise util.UICException("UIC ticket record data too short")
            else:
                data_length = len(data_utf8.encode("utf8", "replace")) + 12
                is_utf8_len = True
        if len(data_utf8) + 12 == data_length:
            data_length = len(data_utf8.encode("utf8", "replace")) + 12
            is_utf8_len = True

        return cls(
            id=record_id,
            version=version,
            data=data[12:data_length],
            is_utf8_len=is_utf8_len,
        )


@dataclasses.dataclass
class Envelope:
    version: int
    issuer_rics: int
    signature_key_id: typing.Union[int, str]
    records: typing.List[Record]
    signature: bytes = None
    signed_data: bytes = None

    def issuer(self):
        return rics.get_rics(self.issuer_rics)

    def signing_cert(self):
        return certs.signing_cert(self.issuer_rics, self.signature_key_id)

    def can_verify(self):
        return bool(certs.public_key(self.issuer_rics, self.signature_key_id))

    def verify_signature(self):
        if not self.signature or not self.signed_data:
            return False

        pk = certs.public_key(self.issuer_rics, self.signature_key_id)
        if not pk:
            return False

        if self.version == 1:
            sig_data = ber_tlv.tlv.Tlv.parse(self.signature, True)
            sig = ber_tlv.tlv.Tlv.build(sig_data)
            hasher = cryptography.hazmat.primitives.hashes.SHA1()
        elif self.version == 2:
            sig = bytearray([0x30, 0x44])
            if self.signature[0] & 0x80:
                sig[1] += 1
                sig.extend([0x02, 0x21, 0x00])
            else:
                sig.extend([0x02, 0x20])
            sig.extend(self.signature[0:32])
            if self.signature[32] & 0x80:
                sig[1] += 1
                sig.extend([0x02, 0x21, 0x00])
            else:
                sig.extend([0x02, 0x20])
            sig.extend(self.signature[32:64])
            sig = bytes(sig)
            hasher = cryptography.hazmat.primitives.hashes.SHA256()
        else:
            return False

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
        if data[:3] != b"#UT":
            raise util.UICException("Invalid UIC ticket magic")

        if len(data) < 64:
            raise util.UICException("UIC ticket too short")

        try:
            version_str = data[3:5].decode("ascii")
            version = int(version_str, 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise util.UICException("Invalid UIC ticket version") from e

        if version not in (1, 2):
            raise util.UICException("Unsupported UIC ticket version")

        try:
            provider_str = data[5:9].decode("ascii")
            provider = int(provider_str, 10)
            signature_key_id_str = data[9:14].decode("ascii")
        except (UnicodeDecodeError, ValueError) as e:
            raise util.UICException("Invalid UIC ticket provider or signature key ID") from e

        try:
            signature_key_id = int(signature_key_id_str, 10)
        except ValueError:
            signature_key_id = signature_key_id_str

        if version == 1:
            signature, data = data[14:64], data[64:]
        elif version == 2:
            signature, data = data[14:78], data[78:]
        else:
            raise util.UICException("Unsupported UIC ticket version")

        try:
            data_length_str = data[0:4].decode("ascii")
            data_length = int(data_length_str, 10)
        except (UnicodeDecodeError, ValueError) as e:
            raise util.UICException("Invalid UIC ticket data length") from e

        if len(data) < 4 + data_length:
            raise util.UICException("UIC ticket data too short")

        signed_data = data[4:]

        try:
            raw_ticket = zlib.decompress(data[4:4+data_length])
        except zlib.error as e:
            raise util.UICException("Failed to decompress UIC ticket data") from e

        offset = 0
        records = []
        while raw_ticket[offset:]:
            record = Record.parse(raw_ticket[offset:])
            offset += 12 + len(record.data)
            records.append(record)

        return cls(
            version=version,
            issuer_rics=provider,
            signature_key_id=signature_key_id,
            signature=signature,
            signed_data=signed_data,
            records=records
        )