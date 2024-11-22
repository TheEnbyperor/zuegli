from django.core.management.base import BaseCommand
import dataclasses
import django.core.files.storage
import niquests
import typing
import xsdata.formats.dataclass.parsers
import xsdata.models.datatype
import json

xml_parser = xsdata.formats.dataclass.parsers.XmlParser()

@dataclasses.dataclass
class ProductOwnerCodes:
    codes: typing.List[typing.Union[int, str]] = dataclasses.field(
        default_factory=list,
        metadata={
            "type": "Elements",
             "choices": (
                 {"name": "productOwnerCode", "type": int},
                 {"name": "productOwnerName", "type": str},
             )
        },
    )


@dataclasses.dataclass
class Key:
    issuer_name: str = dataclasses.field(metadata={"name": "issuerName"})
    issuer_code: int = dataclasses.field(metadata={"name": "issuerCode"})
    version_type: str = dataclasses.field(metadata={"name": "versionType"})
    signature_algorithm: str = dataclasses.field(metadata={"name": "signatureAlgorithm"})
    key_id: str = dataclasses.field(metadata={"name": "id"})
    public_key: bytes = dataclasses.field(metadata={"name": "publicKey", "format": "base64"})
    barcode_version: str = dataclasses.field(metadata={"name": "barcodeVersion"})
    start_date: xsdata.models.datatype.XmlDate = dataclasses.field(metadata={"name": "startDate"})
    end_date: xsdata.models.datatype.XmlDate = dataclasses.field(metadata={"name": "endDate"})
    barcode_xsd: str = dataclasses.field(metadata={"name": "barcodeXsd"})
    allowed_product_owner_codes: ProductOwnerCodes = dataclasses.field(
        metadata={
            "name": "allowedProductOwnerCodes",
            "type": "Element",
        },
    )
    keyForged: bool = dataclasses.field(metadata={"name": "keyForged"})
    comment_for_encryption_type: str = dataclasses.field(metadata={"name": "commentForEncryptionType"})

@dataclasses.dataclass
class Keys:
    class Meta:
        name = "keys"

    key: typing.List[Key] = dataclasses.field(
        default_factory=list,
        metadata={
            "type": "Element",
            "min_occurs": 0,
        },
    )

class Command(BaseCommand):
    help = "Download UIC signing certificates"

    def handle(self, *args, **options):
        uic_storage = django.core.files.storage.storages["uic-data"]

        r = niquests.get("https://railpublickey.uic.org/download.php")
        r.raise_for_status()

        data = xml_parser.from_string(r.text, Keys)
        for key in data.key:
            key_name = f"cert-{key.issuer_code}_{key.key_id}_{key.barcode_version}.der"
            key_meta_name = f"cert-{key.issuer_code}_{key.key_id}_{key.barcode_version}.json"
            with uic_storage.open(key_name, "wb") as f:
                f.write(key.public_key)
            with uic_storage.open(key_meta_name, "w") as f:
                json.dump({
                    "issuer_name": key.issuer_name,
                    "issuer_code": key.issuer_code,
                    "version_type": key.version_type,
                    "signature_algorithm": key.signature_algorithm,
                    "key_id": key.key_id,
                    "barcode_version": key.barcode_version,
                    "start_date": key.start_date.to_date().isoformat(),
                    "end_date": key.end_date.to_date().isoformat(),
                    "allowed_product_owner_codes": key.allowed_product_owner_codes.codes if key.allowed_product_owner_codes else None,
                }, f)