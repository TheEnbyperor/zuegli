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
    valid_from: datetime.datetime
    valid_until: datetime.datetime

    @classmethod
    def from_json(cls, data) -> "Certificate":
        modulus = bytes.fromhex(data["modulus_hex"])
        return cls(
            issuer_id=data["issuer_id"],
            modulus=int.from_bytes(modulus, "big"),
            modulus_len=len(modulus),
            exponent=int(data["public_exponent_hex"], 16),
            valid_from=datetime.datetime.fromisoformat(data["valid_from"]),
            valid_until=datetime.datetime.fromisoformat(data["valid_until"]),
        )


class CertificateStore:
    certificates: typing.Dict[str, typing.List[Certificate]]

    def __init__(self):
        self.certificates = {}

    def load_certificates(self):
        certificates = {}
        certificate_storage = django.core.files.storage.storages["rsp-data"]
        with certificate_storage.open("keys.json", "r") as f:
            data = json.loads(f.read())
            for issuer, keys in data.items():
                keys = list(map(lambda k: Certificate.from_json(k), keys))
                certificates[issuer] = keys
        self.certificates = certificates