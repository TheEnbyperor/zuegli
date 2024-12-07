import niquests
import bs4
import re
import json
import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent

zone_re = re.compile(r"vrrInputFlexbox.+\.setObject\((?P<zone_id>\d+),'TariffZone','(?P<zone_name>[^']+)','[^']+',[^']+,[^']+,'[^']+'\);")

def main():
    r = niquests.get("https://tarif.vrsinfo.de/tbv/vrs/cgi/page/40")
    r.raise_for_status()

    soup = bs4.BeautifulSoup(r.text, "html.parser")
    img_map = soup.find("map", attrs={"name": "imageMapVRR"})
    areas = img_map.find_all("area")

    zones = {}

    for area in areas:
        if m := zone_re.fullmatch(area.attrs["onclick"]):
            zones[int(m.group("zone_id"))] = m.group("zone_name")

    with open(ROOT_DIR / "main" / "vdv" / "data" / "vrs-tarifgebiete.json", "w") as f:
        json.dump(zones, f)

if __name__ == "__main__":
    main()
