from ..uic import stations

def get_db_station_name(code: int):
    if station := stations.get_station_by_db(code):
        return station["name"]

SPACIAL_VALIDITY = {
    5000: {
        1: "Deutschlandweit",
    },
    6262: get_db_station_name
}