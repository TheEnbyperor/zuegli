import camelot
import pathlib
import json

ROOT_DIR = pathlib.Path(__file__).parent.parent

def main():
    data = {}
    tables = camelot.read_pdf(str((ROOT_DIR / "data" / "Leitpunktkuerzel.pdf").absolute()), pages="all")
    for table in tables:
        for row in table.data[1:]:
            data[row[0]] = {
                "name": row[1],
                "ibnr": row[2],
                "verbund": row[3]
            }

    with open(ROOT_DIR / "main" / "uic" / "data" / "db-leitpunktkuerzel.json", "w") as f:
        json.dump(data, f)


if __name__ == '__main__':
    main()