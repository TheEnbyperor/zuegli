import json
import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent

def main():
    with open(ROOT_DIR / "data" / "sz" / "postajalisca.json", "r") as f:
        stations = json.load(f)

    stations_out = {}
    for station in stations:
        stations_out[station["idPostajalisce"]] = int(station["sifra"]) + 7900000

    with open(ROOT_DIR / "uic-data" / "sz-stations.json", "w") as f:
        json.dump(stations_out, f)

    with open(ROOT_DIR / "data" / "sz" / "postajne_tocke.json", "r") as f:
        station_points = json.load(f)

    station_points_map = {}
    for station_point in station_points:
        station_points_map[station_point["idPostajnaTocka"]] = int(station_point["sifra"]) + 7900000

    with open(ROOT_DIR / "data" / "sz" / "relacije_vozlisca.json", "r") as f:
        routes = json.load(f)

    routes_out = {}
    for route in routes:
        origin = station_points_map[route["idPostajnaTockaOd"]]
        destination = station_points_map[route["idPostajnaTockaDo"]]
        via = [station_points_map[v] for v in route["idPostajneTockeVia"]["int"]]
        routes_out[route["idRelacijaVozlisc"]] = [origin, *via, destination]

    with open(ROOT_DIR / "uic-data" / "sz-routes.json", "w") as f:
        json.dump(routes_out, f)


if __name__ == '__main__':
    main()