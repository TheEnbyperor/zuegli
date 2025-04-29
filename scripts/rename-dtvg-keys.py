import pathlib
import os
import cryptography.x509
import re

from cryptography.hazmat.primitives import serialization

ROOT_DIR = pathlib.Path(__file__).parent.parent
KEY_RE = re.compile("^(?P<rics>[0-9]{4})-?(?P<key_id>[a-zA-Z0-9]+).pem$")

def main():
    for filename in os.listdir(ROOT_DIR / "dtvg-certs"):
        if m := KEY_RE.match(filename):
            rics = int(m.group("rics"))
            try:
                key_id = int(m.group("key_id"))
            except ValueError:
                key_id = m.group("key_id")
            new_filename = f"cert-{rics}_{key_id}.der"

            with open(ROOT_DIR / "dtvg-certs" / filename, "rb") as f:
                cert = cryptography.x509.load_pem_x509_certificate(f.read())

            with open(ROOT_DIR / "uic-data" / new_filename, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.DER))

        else:
            print(f"Warning: unrecognized filename {filename}")

if __name__ == "__main__":
    main()