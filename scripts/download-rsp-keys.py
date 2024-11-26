import pathlib
import json
import niquests
import datetime

ROOT_DIR = pathlib.Path(__file__).parent.parent


def main():
    with open(ROOT_DIR / "priv" / "rdg_keys.json") as f:
        login_data = json.load(f)

    r = niquests.get(
        "https://tvd.theticketkeeper.com/download_keys",
        auth=(login_data["username"], login_data["password"])
    )
    r.raise_for_status()

    keys = r.json()

    with open(ROOT_DIR / "scripts" / "extra_rsp_keys.json") as f:
        extra_keys = json.load(f)

    out = {}
    for issuer, issuer_keys in keys["keys"].items():
        if issuer not in out:
            out[issuer] = []

        for issuer_key in issuer_keys:
            out[issuer].append({
                "is_test": True if issuer_key["test_only"] == "Y" else False,
                "issuer_id": issuer,
                "modulus_hex": issuer_key["modulus_hex"].lower(),
                "public_exponent_hex": issuer_key["public_exponent_hex"].lower(),
                "public_key_x509": issuer_key["public_key_x509"],
                "valid_from": datetime.datetime.strptime(issuer_key["valid_from"], "%Y%m%d%H%M%S").isoformat(),
                "valid_until": datetime.datetime.strptime(issuer_key["valid_until"], "%Y%m%d%H%M%S").isoformat(),
            })

    for issuer, issuer_keys in extra_keys.items():
        if issuer not in out:
            out[issuer] = []

        out[issuer].extend(issuer_keys)

    with open(ROOT_DIR / "rsp-data" / "keys.json", "w") as f:
        json.dump(out, f)


if __name__ == '__main__':
    main()
