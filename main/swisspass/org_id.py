import typing
import pathlib
import json

ORG_IDS = None
ROOT_DIR = pathlib.Path(__file__).parent

def get_org_ids_list() -> typing.Dict[str, dict]:
    global ORG_IDS

    if ORG_IDS:
        return ORG_IDS

    with open(ROOT_DIR / "data" / "orgs.json", "r") as f:
        ORG_IDS = json.loads(f.read())

    return ORG_IDS


def get_org(code: int) -> typing.Optional[dict]:
    org_list = get_org_ids_list()
    if org := org_list.get(f"{code:03d}"):
        return org
