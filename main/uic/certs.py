import cryptography.x509
import cryptography.exceptions
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.serialization
import django.core.files.storage
import json


def signing_cert(rics: int, key_id: int):
    uic_storage = django.core.files.storage.storages["uic-data"]
    key_name = f"cert-{rics}_{key_id}.der"
    key_meta_name = f"cert-{rics}_{key_id}.json"
    if uic_storage.exists(key_meta_name):
        with uic_storage.open(key_meta_name) as key_file:
            meta = json.load(key_file)
        with uic_storage.open(key_name) as key_file:
            key = cryptography.x509.load_der_x509_certificate(key_file.read())

        return meta, key


def public_key(rics: int, key_id: int):
    uic_storage = django.core.files.storage.storages["uic-data"]
    cert_name = f"cert-{rics}_{key_id}.der"
    key_name = f"pk-{rics}_{key_id}.der"

    try:
        with uic_storage.open(cert_name) as key_file:
            try:
                key = cryptography.x509.load_der_x509_certificate(key_file.read())
            except ValueError:
                return None

        return key.public_key()
    except FileNotFoundError:
        try:
            with uic_storage.open(key_name) as key_file:
                try:
                    key = cryptography.hazmat.primitives.serialization.load_der_public_key(key_file.read())
                except ValueError:
                    return None

            return key
        except FileNotFoundError:
            return None
