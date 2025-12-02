from django.conf import settings

GTFS_FEEDS = {
    "eil": "https://integration-storage.dm.eurostar.com/gtfs-prod/gtfs_static_commercial_v2.zip",
    "mav": {
        "url": "https://www.mavcsoport.hu/gtfs/gtfsMavMenetrend.zip",
        "username": settings.MAV_GTFS_USERNAME,
        "password": settings.MAV_GTFS_PASSWORD,
    }
#    "oebb": "https://static.web.oebb.at/open-data/soll-fahrplan-gtfs/GTFS_OP_2025_obb.zip",
}
GTFS_RT_FEEDS = {
    "eil": "https://integration-storage.dm.eurostar.com/gtfs-prod/gtfs_rt_v2.json"
}
