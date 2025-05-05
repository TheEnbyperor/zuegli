import dataclasses
import json
import datetime
import typing
import django.core.files.storage


@dataclasses.dataclass
class Certificate:
    issuer_id: str
    modulus: int
    modulus_len: int
    exponent: int

    @classmethod
    def from_json(cls, data) -> "Certificate":
        modulus = bytes.fromhex(data["modulus_hex"])
        return cls(
            issuer_id=data["issuer_id"],
            modulus=int.from_bytes(modulus, "big"),
            modulus_len=len(modulus),
            exponent=int(data["public_exponent_hex"], 16),
        )


class CertificateStore:
    certificates: typing.Dict[str, typing.List[Certificate]]

    def __init__(self):
        self.certificates = {}

PKI_STORE = None

def get_pki_store():
    global PKI_STORE

    if PKI_STORE is not None:
        return PKI_STORE

    pki_store = CertificateStore()

    pki_store.certificates["M0"] = [Certificate.from_json({
        "issuer_id": "M0",
        "modulus_hex": "a36cb7268d83a04294f4dd79951c6106b9a0cf1caa8b43da756e8df25cb21a849259a4c0a2ab985dc998ec66b51217b1578ed3c8e463a9669f6cc30fa079fdecf97cd33d7336a6d27df1e157bdf76a6fd8358fb44f54ffeaf7bd6740b85360ed10ae5e2b9538c5fb2934aae869893e96128fe76a613e605461143f56cf7e649f",
        "public_exponent_hex": "10001"
    })]

    PKI_STORE = pki_store

    return pki_store
