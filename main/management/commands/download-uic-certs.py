from django.core.management.base import BaseCommand
import django.core.files.storage
import niquests
import xsdata.formats.dataclass.parsers
import xsdata.models.datatype
import json
import main.uic.gen.bar_code_key_exchange

xml_parser = xsdata.formats.dataclass.parsers.XmlParser()

class Command(BaseCommand):
    help = "Download UIC signing certificates"

    def handle(self, *args, **options):
        uic_storage = django.core.files.storage.storages["uic-data"]

        r = niquests.get("https://railpublickey.uic.org/download.php")
        r.raise_for_status()

        data = xml_parser.from_string(r.text, main.uic.gen.bar_code_key_exchange.Keys)
        for key in data.key:
            if key.public_key.keytype != "CERTIFICATE":
                continue
            key_name = f"cert-{key.issuer_code}_{key.id}.der"
            key_meta_name = f"cert-{key.issuer_code}_{key.id}.json"
            with uic_storage.open(key_name, "wb") as f:
                f.write(key.public_key.value)
            with uic_storage.open(key_meta_name, "w") as f:
                json.dump({
                    "issuer_name": key.issuer_name,
                    "issuer_code": key.issuer_code,
                    "version_type": key.version_type,
                    "signature_algorithm": key.signature_algorithm,
                    "key_id": key.id,
                    "barcode_version": key.barcode_version,
                    "start_date": key.start_date.to_date().isoformat(),
                    "end_date": key.end_date.to_date().isoformat(),
                    "allowed_product_owner_codes": key.allowed_product_owner_codes.product_owner_code if key.allowed_product_owner_codes.product_owner_code else None,
                    "allowed_product_owner_name": key.allowed_product_owner_codes.product_owner_name if key.allowed_product_owner_codes.product_owner_name else None,
                }, f)