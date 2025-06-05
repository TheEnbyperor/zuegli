import pathlib
import json

ROOT_DIR = pathlib.Path(__file__).parent.parent

STATION_UIC = {
    "Vinko": 71160,
    "Zapre": 74004,
    "BJar": 72503,
    "Oguli": 75460,
    "SVrp": 71104,
    "ZgGK": 72480,
    "NKB": 72708,
    "Dalj": 71207,
    "Oštar": 75111,
    "Osije": 71960,
    "Bjvar": 73307,
    "Varaž": 74460,
    "Kopri": 73160,
    "Sunja": 72060,
}

def main():
    with open(ROOT_DIR / "data" / "stationgroupops_version259.txt") as f:
        lines = f.readlines()

    out = {}

    lines = [lines.strip().split(":", 1) for lines in lines]
    for group_id, stations in lines:
        group_id = int(group_id, 10)
        if stations == "-":
            out[group_id] = []
        else:
            stations = stations.split("*")
            stations = [STATION_UIC[s] + 7800000 for s in stations]
            out[group_id] = stations

    with open(ROOT_DIR / "main" / "hzpp" / "codes" / "routes.json", "w") as f:
        json.dump(out, f)

if __name__ == '__main__':
    main()