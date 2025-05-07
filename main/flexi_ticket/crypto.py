import secrets
import typing

import cryptography.hazmat.primitives.cmac
import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.ciphers.algorithms
import cryptography.hazmat.primitives.ciphers.modes
from . import util

def rsa(blob: bytes, exponent: int, modulus: int) -> bytes:
    k = (modulus.bit_length() + 7) // 8
    if len(blob) < k:
        raise util.FTException(f"Input must be at least {k} bytes")

    first, rest = blob[:k], blob[k:]

    block = bytearray(first)
    block[0] = 0

    m = int.from_bytes(block, "big")
    c = pow(m, exponent, modulus)
    encrypted_block = c.to_bytes(k, "big")

    return encrypted_block + rest

def aes_encrypt_and_prepend_key(key: bytes, data: bytes) -> bytes:
    if len(key) != 32:
        raise util.FTException("Key must be 32 bytes")

    data_len = len(data)
    full_len = data_len + 36 + 8
    if full_len < 128:
        pad = 128 - full_len
    else:
        pad = (16 - (full_len % 16)) % 16

    region_len = full_len + pad
    working = bytearray(region_len)
    working[0:32] = key
    working[32:36] = data_len.to_bytes(4, "big")
    working[36:36+data_len] = data
    working[36+data_len:36+data_len+pad] = secrets.token_bytes(pad)

    cmac = cryptography.hazmat.primitives.cmac.CMAC(
        cryptography.hazmat.primitives.ciphers.algorithms.AES(key)
    )
    cmac.update(working[32:region_len-8])
    tag = cmac.finalize()[:8]
    working[region_len-8 : region_len] = tag

    iv = bytes([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    cipher = cryptography.hazmat.primitives.ciphers.Cipher(
        cryptography.hazmat.primitives.ciphers.algorithms.AES(key),
        cryptography.hazmat.primitives.ciphers.modes.CFB(iv)
    )
    encryptor = cipher.encryptor()
    enc = encryptor.update(bytes(working[32:])) + encryptor.finalize()

    return b"\x00" + key + enc


def aes_decrypt(key: bytes, ciphertext: bytes, iv: typing.Optional[bytes] = None) -> bytes:
    if iv is None:
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
