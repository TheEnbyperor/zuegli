import hashlib
import json
import typing
import zipfile
import io
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.serialization.pkcs7
from django.conf import settings

class PKPass:
    def __init__(self):
        self.data = {}
        self.manifest = {}
        self.signature = None

    def add_file(self, filename: str, data: bytes):
        file_hash = hashlib.sha1(data).hexdigest()
        self.data[filename] = data
        self.manifest[filename] = file_hash

    def sign(self):
        manifest = json.dumps(self.manifest).encode("utf-8")
        self.data["manifest.json"] = manifest
        signature = cryptography.hazmat.primitives.serialization.pkcs7.PKCS7SignatureBuilder()\
                .set_data(manifest)\
                .add_signer(
                    settings.PKPASS_CERTIFICATE, settings.PKPASS_KEY,
                    cryptography.hazmat.primitives.hashes.SHA256()
                )\
                .add_certificate(settings.WWDR_CERTIFICATE)\
                .sign(cryptography.hazmat.primitives.serialization.Encoding.DER, [
                    cryptography.hazmat.primitives.serialization.pkcs7.PKCS7Options.Binary,
                    cryptography.hazmat.primitives.serialization.pkcs7.PKCS7Options.DetachedSignature,
                ])
        self.data["signature"] = signature

    def get_buffer(self) -> bytes:
        zip_buffer = io.BytesIO()
        zip = zipfile.ZipFile(zip_buffer, "w")
        for filename, data in self.data.items():
            zip.writestr(filename, data)
        zip.close()
        return zip_buffer.getvalue()


class MultiPKPass:
    def __init__(self):
        self.counter = 1
        self.zip_buffer = io.BytesIO()
        self.zip = zipfile.ZipFile(self.zip_buffer, "w")

    def add_pkpass(self, pkpass: typing.Union[PKPass, bytes]):
        if isinstance(pkpass, PKPass):
            self.zip.writestr(f"pass-{self.counter}.pkpass", pkpass.get_buffer())
        else:
            self.zip.writestr(f"pass-{self.counter}.pkpass", pkpass)
        self.counter += 1

    def get_buffer(self) -> bytes:
        self.zip.close()
        return self.zip_buffer.getvalue()