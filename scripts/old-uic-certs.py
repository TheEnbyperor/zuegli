import pathlib
import xsdata.formats.dataclass.parsers
import xsdata.models.datatype
import json
import sys
import django

ROOT_DIR = pathlib.Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
django.setup()

from main.uic.gen import bar_code_key_exchange

xml_parser = xsdata.formats.dataclass.parsers.XmlParser()


def main():
    with open(ROOT_DIR / "data" / "keysold.xml") as f:
        d = f.read()

    data = xml_parser.from_string(d, bar_code_key_exchange.Keys)
    for key in data.key:
        if key.public_key.keytype != "CERTIFICATE":
            continue
        key_name = f"cert-{key.issuer_code}_{key.id}.der"
        key_meta_name = f"cert-{key.issuer_code}_{key.id}.json"
        with open(ROOT_DIR / "uic-data" / key_name, "wb") as f:
            f.write(key.public_key.value)
        with open(ROOT_DIR / "uic-data" / key_meta_name, "w") as f:
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


if __name__ == "__main__":
    main()