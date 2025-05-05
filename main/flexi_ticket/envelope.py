import dataclasses
import base26
import hashlib
import typing
import cryptography.hazmat.primitives.cmac
import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.ciphers.algorithms
import cryptography.hazmat.primitives.ciphers.modes
from . import util, pki

@dataclasses.dataclass
class Data:
    data: bytes
    extra_data: typing.Optional[bytes] = None

@dataclasses.dataclass
class Envelope:
    issuer_id: str
    payload: bytes

    @classmethod
    def parse(cls, d: bytes) -> "Envelope":
        if len(d) < 4:
            raise util.FTException("Envelope is too short")

        if d[0:2] != b"FT":
            raise util.FTException("Envelope isn't a Flexi-ticket")

        try:
            issuer_id = d[2:4].decode()
        except UnicodeDecodeError as e:
            raise util.FTException("Invalid key ID encoding") from e

        try:
            payload = base26.decode(d[4:].decode())
        except UnicodeDecodeError as e:
            raise util.FTException("Invalid payload encoding") from e

        return cls(
            issuer_id=issuer_id,
            payload=payload,
        )

    def decrypt_with_cert(self, cert: pki.Certificate) -> typing.Optional[Data]:
        payload = self.payload[:128]
        h = int.from_bytes(payload, 'big')
        m = pow(h, cert.exponent, cert.modulus)
        data = m.to_bytes(cert.modulus_len, 'big')

        if data[0] != 0:
            return None

        if data[1] == 1:
            offset = 2
            while data[offset] == 0xFF:
                offset += 1
            if data[offset] == 0:
                data = data[offset+1:]
            else:
                return None
        elif data[1] == 2:
            offset = 2
            while data[offset] != 0x00:
                offset += 1
            data = data[offset+1:]
        else:
            return None

        if data[0] != 0x00:
            raise util.FTException("Invalid message format")
        message_hash = data[1:9]

        if data[9] != 0x01:
            raise util.FTException("Invalid message format")
        data = data[10:]

        if hashlib.sha256(data).digest()[:8] != message_hash:
            raise util.FTException("Invalid message integrity hash")

        if extra := self.payload[128:]:
            if extra[0] & 3 != 1 or (extra[0] >> 2) & 3 != 1:
                raise util.FTException("Invalid extra data")

            start = len(payload) // 2 - 16
            if start < 0 or start + 32 > len(payload):
                raise util.FTException("Payload too short to extract AES key")
            aes_key = payload[start:start + 32]
            extra = aes_decrypt(aes_key, extra[1:])
        else:
            extra = None

        return Data(
            data=data,
            extra_data=extra
        )

def aes_decrypt(key: bytes, ciphertext: bytes) -> bytes:
    iv = bytes([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    cipher = cryptography.hazmat.primitives.ciphers.Cipher(
        cryptography.hazmat.primitives.ciphers.algorithms.AES(key),
        cryptography.hazmat.primitives.ciphers.modes.CFB(iv)
    )
    decrypt = cipher.decryptor()
    buf = decrypt.update(ciphertext) + decrypt.finalize()

    if len(buf) < 12:
        raise util.FTException("Ciphertext too short")
    tag = buf[-8:]
    msg_plus_len = buf[:-8]

    cmac = cryptography.hazmat.primitives.cmac.CMAC(
        cryptography.hazmat.primitives.ciphers.algorithms.AES(key)
    )
    cmac.update(msg_plus_len)
    expected_tag = cmac.finalize()[:8]
    if expected_tag != tag:
        raise util.FTException("CMAC verification failed")

    length = int.from_bytes(msg_plus_len[0:4], 'big')
    max_data = len(msg_plus_len) - 4
    if length < 0 or length > max_data:
        raise util.FTException(f"Invalid plaintext length: {length}")
    return msg_plus_len[4:4 + length]
