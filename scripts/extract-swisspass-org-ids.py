import camelot
import pathlib
import json

ROOT_DIR = pathlib.Path(__file__).parent.parent

def main():
    data = {}
    tables = camelot.read_pdf(str((ROOT_DIR / "data" / "Anwendungsbereiche_d.pdf").absolute()), pages="all")
    for table in tables:
        for row in table.data[1:]:
            data[row[1]] = {
                "name": row[2].replace("-\n", "").replace("\n", " "),
                "short_name": row[0].replace("-\n", "").replace("\n", " "),
            }

    with open(ROOT_DIR / "main" / "swisspass" / "data" / "orgs.json", "w") as f:
        json.dump(data, f)


if __name__ == '__main__':
    main()