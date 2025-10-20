import csv
import re
import zipfile
import io
import datetime
import google.protobuf.json_format
import pytz
import django.db
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import Q
from . import models, data
from .proto.gtfs.proto import gtfs_rt_pb2
from main import session

logger = get_task_logger(__name__)

TIME_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})$")


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=3, default_retry_delay=3,
    ignore_result=True
)
def process_gtfs(feed_id: str, feed_url: str):
    r = session.get(feed_url, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    r.raise_for_status()
    gtfs_zip = zipfile.ZipFile(io.BytesIO(r.content))

    filenames = [f.filename for f in gtfs_zip.filelist]

    objs = []
    seen_ids = []
    with gtfs_zip.open("agency.txt") as f:
        data = csv.DictReader(io.TextIOWrapper(f, "utf-8-sig"))
        for row in data:
            seen_ids.append(row["agency_id"])
            objs.append(models.Agency(
                feed_id=feed_id,
                agency_id=row["agency_id"],
                name=row["agency_name"],
                url=row["agency_url"],
                timezone=row["agency_timezone"],
                primary_language=row.get("agency_language"),
                phone=row.get("agency_phone"),
                fare_url=row.get("agency_fare_url"),
                email=row.get("agency_email"),
            ))
    agency_cache = {}
    for r in models.Agency.objects.bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=("feed_id", "agency_id"),
        update_fields=("name", "url", "timezone", "primary_language", "phone", "fare_url", "email"),
    ):
        if r.pk:
            agency_cache[r.agency_id] = r
    models.Agency.objects.filter(Q(feed_id=feed_id) & ~Q(agency_id__in=seen_ids)).delete()
    logger.info(f"Imported {len(objs)} agencies")

    objs = []
    seen_ids = []
    station_cache = {}
    with gtfs_zip.open("stops.txt") as f:
        data = list(csv.DictReader(io.TextIOWrapper(f, "utf-8-sig")))
        for row in data:
            location_type = row.get("location_type")
            if not location_type or location_type == "0":
                location_type = models.Stop.LOCATION_TYPE_STOP
            elif location_type == "1":
                location_type = models.Stop.LOCATION_TYPE_STATION
            elif location_type == "2":
                location_type = models.Stop.LOCATION_TYPE_ENTRANCE
            elif location_type == "3":
                location_type = models.Stop.LOCATION_TYPE_GENERIC_NODE
            elif location_type == "4":
                location_type = models.Stop.LOCATION_TYPE_BOARDING_AREA
            else:
                raise ValueError(f"Invalid location type: {location_type}")

            wheelchair_boarding = row.get("wheelchair_boarding")
            if not wheelchair_boarding or wheelchair_boarding == "0":
                wheelchair_boarding = None
            elif wheelchair_boarding == "1":
                wheelchair_boarding = True
            elif wheelchair_boarding == "2":
                wheelchair_boarding = False
            else:
                raise ValueError(f"Invalid wheelchair boarding: {wheelchair_boarding}")

            objs.append(models.Stop(
                feed_id=feed_id,
                stop_id=row["stop_id"],
                code=row.get("stop_code"),
                name=row.get("stop_name"),
                tts_name=row.get("tts_stop_name"),
                description=row.get("stop_desc"),
                lat=row.get("stop_lat"),
                long=row.get("stop_lon"),
                url=row.get("stop_url"),
                location_type=location_type,
                timezone=row.get("stop_timezone"),
                wheelchair_boarding=wheelchair_boarding,
                platform_code=row.get("platform_code"),
            ))
            seen_ids.append(row["stop_id"])
    for r in models.Stop.objects.bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=("feed_id", "stop_id"),
        update_fields=("code", "name", "tts_name", "description", "lat", "long", "url", "location_type", "timezone", "wheelchair_boarding", "platform_code"),
    ):
        if r.pk:
            station_cache[r.stop_id] = r
    for row, obj in zip(data, objs):
        if parent_station_id := row.get("parent_station"):
            if parent_station_id not in station_cache:
                parent_station = models.Stop.objects.get(feed_id=feed_id, stop_id=parent_station_id)
                station_cache[parent_station_id] = parent_station
            else:
                parent_station = station_cache[parent_station_id]
        else:
            parent_station = None
        obj.parent_station = parent_station
    models.Stop.objects.bulk_update(objs, fields=("parent_station",))
    models.Stop.objects.filter(Q(feed_id=feed_id) & ~Q(stop_id__in=seen_ids)).delete()
    logger.info(f"Imported {len(objs)} stops")

    objs = []
    seen_ids = []
    route_cache = {}
    with gtfs_zip.open("routes.txt") as f:
        data = csv.DictReader(io.TextIOWrapper(f, "utf-8-sig"))
        for row in data:
            if row["agency_id"] not in agency_cache:
                agency = models.Agency.objects.get(feed_id=feed_id, agency_id=row["agency_id"])
                agency_cache[row["agency_id"]] = agency
            else:
                agency = agency_cache[row["agency_id"]]

            route_type = row.get("route_type")
            if route_type == "0":
                route_type = models.Route.ROUTE_TYPE_LIGHT_RAIL
            elif route_type == "1":
                route_type = models.Route.ROUTE_TYPE_METRO
            elif route_type == "2":
                route_type = models.Route.ROUTE_TYPE_RAIL
            elif route_type == "3":
                route_type = models.Route.ROUTE_TYPE_BUS
            elif route_type == "4":
                route_type = models.Route.ROUTE_TYPE_FERRY
            elif route_type == "5":
                route_type = models.Route.ROUTE_TYPE_CABLE_TRAM
            elif route_type == "6":
                route_type = models.Route.ROUTE_TYPE_AERIAL_LIFT
            elif route_type == "7":
                route_type = models.Route.ROUTE_TYPE_FUNICULAR
            elif route_type == "11":
                route_type = models.Route.ROUTE_TYPE_TROLLEYBUS
            elif route_type == "12":
                route_type = models.Route.ROUTE_TYPE_MONORAIL
            else:
                raise ValueError(f"Invalid route type: {route_type}")

            objs.append(models.Route(
                feed_id=feed_id,
                route_id=row["route_id"],
                agency=agency,
                short_name=row.get("route_short_name"),
                long_name=row.get("route_long_name"),
                description=row.get("route_desc"),
                route_type=route_type,
                url=row.get("route_url"),
                colour=row.get("route_color"),
                text_colour=row.get("route_text_color"),
                sort_order=row.get("route_sort_order"),
            ))
            seen_ids.append(row["route_id"])
    for r in models.Route.objects.bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=("feed_id", "route_id"),
        update_fields=("agency", "short_name", "long_name", "description", "route_type", "url", "colour", "text_colour", "sort_order"),
    ):
        if r.pk:
            route_cache[r.route_id] = r
    models.Route.objects.filter(Q(feed_id=feed_id) & ~Q(route_id__in=seen_ids)).delete()
    logger.info(f"Imported {len(objs)} routes")

    seen_calendar_ids = []
    calendar_cache = {}
    if "calendar.txt" in filenames:
        objs = []
        with gtfs_zip.open("calendar.txt") as f:
            data = csv.DictReader(io.TextIOWrapper(f, "utf-8-sig"))
            for row in data:
                monday = row["monday"]
                if monday == "0":
                    monday = False
                elif monday == "1":
                    monday = True
                else:
                    raise ValueError(f"Invalid Monday availability: {monday}")

                tuesday = row["tuesday"]
                if tuesday == "0":
                    tuesday = False
                elif tuesday == "1":
                    tuesday = True
                else:
                    raise ValueError(f"Invalid Tuesday availability: {tuesday}")

                wednesday = row["wednesday"]
                if wednesday == "0":
                    wednesday = False
                elif wednesday == "1":
                    wednesday = True
                else:
                    raise ValueError(f"Invalid Wednesday availability: {wednesday}")

                thursday = row["thursday"]
                if thursday == "0":
                    thursday = False
                elif thursday == "1":
                    thursday = True
                else:
                    raise ValueError(f"Invalid Thursday availability: {thursday}")

                friday = row["friday"]
                if friday == "0":
                    friday = False
                elif friday == "1":
                    friday = True
                else:
                    raise ValueError(f"Invalid Friday availability: {friday}")

                saturday = row["saturday"]
                if saturday == "0":
                    saturday = False
                elif saturday == "1":
                    saturday = True
                else:
                    raise ValueError(f"Invalid Saturday availability: {saturday}")

                sunday = row["sunday"]
                if sunday == "0":
                    sunday = False
                elif sunday == "1":
                    sunday = True
                else:
                    raise ValueError(f"Invalid Sunday availability: {sunday}")

                objs.append(models.Calendar(
                    feed_id=feed_id,
                    calendar_id=row["service_id"],
                    monday=monday,
                    tuesday=tuesday,
                    wednesday=wednesday,
                    thursday=thursday,
                    friday=friday,
                    saturday=saturday,
                    sunday=sunday,
                    start_date=datetime.datetime.strptime(row["start_date"], "%Y%m%d").date(),
                    end_date=datetime.datetime.strptime(row["end_date"], "%Y%m%d").date(),
                ))
                seen_calendar_ids.append(row["service_id"])
        for r in models.Calendar.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=("feed_id", "calendar_id"),
            update_fields=("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"),
        ):
            if r.pk:
                calendar_cache[r.calendar_id] = r
        models.Calendar.objects.filter(Q(feed_id=feed_id) & ~Q(calendar_id__in=seen_calendar_ids)).delete()
        logger.info(f"Imported {len(objs)} calendars")

    calendar_date_cache = {}
    if "calendar_dates.txt" in filenames:
        objs1 = []
        objs2 = []
        objs2_k = set()
        seen_ids = []
        seen_dates = {}
        with gtfs_zip.open("calendar_dates.txt") as f:
            data = csv.DictReader(io.TextIOWrapper(f, "utf-8-sig"))
            for row in data:
                if row["service_id"] not in seen_calendar_ids:
                    calendar = None
                    calendar_id = row["service_id"]
                else:
                    if row["service_id"] not in calendar_cache:
                        calendar = models.Calendar.objects.filter(feed_id=feed_id, calendar_id=row["service_id"]).first()
                        calendar_cache[row["service_id"]] = calendar
                    else:
                        calendar = calendar_cache[row["service_id"]]
                    calendar_id = None

                exception_type = row["exception_type"]
                if exception_type == "1":
                    exception_type = models.CalendarException.SERVICE_ADDED
                elif exception_type == "2":
                    exception_type = models.CalendarException.SERVICE_REMOVED
                else:
                    raise ValueError(f"Invalid exception type: {exception_type}")

                date = datetime.datetime.strptime(row["date"], "%Y%m%d").date()
                if calendar:
                    objs1.append(models.CalendarException(
                        feed_id=feed_id,
                        calendar=calendar,
                        date=date,
                        exception=exception_type,
                    ))
                    if calendar not in seen_dates:
                        seen_dates[calendar] = []
                    seen_dates[calendar].append(date)
                else:
                    k = (feed_id, calendar_id, date)
                    if k not in objs2_k:
                        objs2_k.add(k)
                        objs2.append(models.CalendarDate(
                            feed_id=feed_id,
                            service_id=calendar_id,
                            date=date,
                            exception=exception_type,
                        ))
                        seen_ids.append(calendar_id)
        models.CalendarException.objects.bulk_create(
            objs1,
            update_conflicts=True,
            unique_fields=("feed_id", "calendar", "date"),
            update_fields=("exception",),
        )
        for r in models.CalendarDate.objects.bulk_create(
            objs2,
            update_conflicts=True,
            unique_fields=("feed_id", "service_id", "date"),
            update_fields=("exception",),
        ):
            if r.pk:
                calendar_date_cache[r.service_id] = r
        for c, dates in seen_dates.items():
            models.CalendarException.objects.filter(Q(feed_id=feed_id) & Q(calendar_id=c) & ~Q(date__in=dates)).delete()
        models.CalendarDate.objects.filter(Q(feed_id=feed_id) & ~Q(service_id__in=seen_ids)).delete()
        logger.info(f"Imported {len(objs1)} calendar exceptions")
        logger.info(f"Imported {len(objs2)} calendar dates")

    shape_cache = {}
    if "shapes.txt" in filenames:
        with gtfs_zip.open("shapes.txt") as f:
            objs = []
            seen_ids = set()
            data = list(csv.DictReader(io.TextIOWrapper(f, "utf-8-sig")))
            for row in data:
                if row["shape_id"] not in seen_ids:
                    objs.append(models.Shape(
                        feed_id=feed_id,
                        shape_id=row["shape_id"],
                    ))
                    seen_ids.add(row["shape_id"])
            to_lookup = set()
            for r in models.Shape.objects.bulk_create(
                objs,
                ignore_conflicts=True,
                unique_fields=("feed_id", "shape_id"),
            ):
                if r.pk:
                    shape_cache[r.shape_id] = r
                else:
                    to_lookup.add(r.shape_id)
            for r in models.Shape.objects.filter(feed_id=feed_id, shape_id__in=to_lookup):
                shape_cache[r.shape_id] = r
            models.Shape.objects.filter(Q(feed_id=feed_id) & ~Q(shape_id__in=seen_ids)).delete()
            objs = []
            for row in data:
                if row["shape_id"] not in shape_cache:
                    shape = models.Shape.objects.get(feed_id=feed_id, shape_id=row["shape_id"])
                    shape_cache[row["shape_id"]] = shape
                else:
                    shape = shape_cache[row["shape_id"]]
                objs.append(models.ShapePoint(
                    shape=shape,
                    sequence=row["shape_pt_sequence"],
                    lat=row["shape_pt_lat"],
                    lon=row["shape_pt_lon"],
                ))
            models.ShapePoint.objects.bulk_create(
                objs,
                update_conflicts=True,
                unique_fields=("shape", "sequence"),
                update_fields=("lat", "lon"),
            )
            logger.info(f"Imported {len(objs)} shape points")

    objs = []
    seen_ids = []
    objs_k = set()
    trip_cache = {}
    with gtfs_zip.open("trips.txt") as f:
        data = csv.DictReader(io.TextIOWrapper(f, "utf-8-sig"))
        for row in data:
            if row["route_id"] not in route_cache:
                route = models.Route.objects.get(feed_id=feed_id, route_id=row["route_id"])
                route_cache[row["route_id"]] = route
            else:
                route = route_cache[row["route_id"]]

            if row["service_id"] in calendar_cache:
                calendar = calendar_cache[row["service_id"]]
                calendar_date = None
            elif row["service_id"] in calendar_date_cache:
                calendar = None
                calendar_date = calendar_date_cache[row["service_id"]]
            else:
                calendar_qs = models.Calendar.objects.filter(feed_id=feed_id, calendar_id=row["service_id"])
                calendar_date_qs = models.CalendarDate.objects.filter(feed_id=feed_id, service_id=row["service_id"])
                if calendar_qs.count():
                    calendar = calendar_qs[0]
                    calendar_date = None
                elif calendar_date_qs.count():
                    calendar = None
                    calendar_date = calendar_date_qs[0]
                else:
                    raise Exception(f"No calendar found for service ID {row['service_id']}")

            direction_id = row.get("direction_id")
            if direction_id is None:
                direction_id = models.Trip.DIRECTION_UNSPECIFIED
            elif direction_id == "0":
                direction_id = models.Trip.DIRECTION_OUTBOUND
            elif direction_id == "1":
                direction_id = models.Trip.DIRECTION_INBOUND
            else:
                raise ValueError(f"Invalid direction ID: {direction_id}")

            wheelchair_accessible = row.get("wheelchair_accessible")
            if not wheelchair_accessible or wheelchair_accessible == "0":
                wheelchair_accessible = None
            elif wheelchair_accessible == "1":
                wheelchair_accessible = True
            elif wheelchair_accessible == "2":
                wheelchair_accessible = False
            else:
                raise ValueError(f"Invalid wheelchair accessible: {wheelchair_accessible}")

            bikes_allowed = row.get("bikes_allowed")
            if not bikes_allowed or bikes_allowed == "0":
                bikes_allowed = None
            elif bikes_allowed == "1":
                bikes_allowed = True
            elif bikes_allowed == "2":
                bikes_allowed = False
            else:
                raise ValueError(f"Invalid bikes allowed: {bikes_allowed}")

            cars_allowed = row.get("cars_allowed")
            if not cars_allowed or cars_allowed == "0":
                cars_allowed = None
            elif cars_allowed == "1":
                cars_allowed = True
            elif cars_allowed == "2":
                cars_allowed = False
            else:
                raise ValueError(f"Invalid cars allowed: {cars_allowed}")

            if shape_id := row.get("shape_id"):
                if row["shape_id"] in shape_cache:
                    shape = shape_cache[row["shape_id"]]
                else:
                    shape = models.Shape.objects.get(feed_id=feed_id, shape_id=shape_id)
                    shape_cache[row["shape_id"]] = shape
            else:
                shape = None

            k = (feed_id, row["trip_id"])
            if k not in objs_k:
                objs_k.add(k)
                objs.append(models.Trip(
                    feed_id=feed_id,
                    trip_id=row["trip_id"],
                    route=route,
                    calendar=calendar,
                    calendar_date=calendar_date,
                    headsign=row.get("trip_headsign"),
                    short_name=row.get("trip_short_name"),
                    direction=direction_id,
                    block_id=row.get("block_id"),
                    wheelchair_accessible=wheelchair_accessible,
                    bikes_allowed=bikes_allowed,
                    cars_allowed=cars_allowed,
                    shape=shape,
                ))
                seen_ids.append(row["trip_id"])
    for r in models.Trip.objects.bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=("feed_id", "trip_id"),
        update_fields=("route", "calendar", "calendar_date", "headsign", "short_name", "direction", "block_id", "wheelchair_accessible", "bikes_allowed", "cars_allowed", "shape"),
    ):
        if r.pk:
            trip_cache[r.trip_id] = r
    models.Trip.objects.filter(Q(feed_id=feed_id) & ~Q(trip_id__in=seen_ids)).delete()
    logger.info(f"Imported {len(seen_ids)} trips")

    objs = []
    objs_k = set()
    seen_ids = {}
    with gtfs_zip.open("stop_times.txt") as f:
        data = csv.DictReader(io.TextIOWrapper(f, "utf-8-sig"))
        for row in data:
            if row["trip_id"] not in trip_cache:
                trip = models.Trip.objects.get(feed_id=feed_id, trip_id=row["trip_id"])
                trip_cache[row["trip_id"]] = trip
            else:
                trip = trip_cache[row["trip_id"]]
            if row["stop_id"] not in station_cache:
                stop = models.Stop.objects.get(feed_id=feed_id, stop_id=row["stop_id"])
                station_cache[row["stop_id"]] = stop
            else:
                stop = station_cache[row["stop_id"]]

            if arrival_time := row.get("arrival_time"):
                if m := TIME_RE.fullmatch(arrival_time):
                    arrival_time = int(m.group(3)) + (60 * int(m.group(2))) + (60 * 60 * int(m.group(1)))
                else:
                    raise ValueError(f"Invalid arrival time: {arrival_time}")
            else:
                arrival_time = None

            if departure_time := row.get("departure_time"):
                if m := TIME_RE.fullmatch(departure_time):
                    departure_time = int(m.group(3)) + (60 * int(m.group(2))) + (60 * 60 * int(m.group(1)))
                else:
                    raise ValueError(f"Invalid departure time: {departure_time}")
            else:
                departure_time = None

            pick_up_type = row.get("pickup_type")
            if not pick_up_type or pick_up_type == "0":
                pick_up_type = models.StopTime.PICK_UP_DROP_OFF_TYPE_REGULAR
            elif pick_up_type == "1":
                pick_up_type = models.StopTime.PICK_UP_DROP_OFF_TYPE_FORBIDDEN
            elif pick_up_type == "2":
                pick_up_type = models.StopTime.PICK_UP_DROP_OFF_TYPE_PHONE
            elif pick_up_type == "3":
                pick_up_type = models.StopTime.PICK_UP_DROP_OFF_TYPE_COORDINATE_WITH_DRIVER
            else:
                raise ValueError(f"Invalid pickup type: {pick_up_type}")

            drop_off_type = row.get("drop_off_type")
            if not drop_off_type or drop_off_type == "0":
                drop_off_type = models.StopTime.PICK_UP_DROP_OFF_TYPE_REGULAR
            elif drop_off_type == "1":
                drop_off_type = models.StopTime.PICK_UP_DROP_OFF_TYPE_FORBIDDEN
            elif drop_off_type == "2":
                drop_off_type = models.StopTime.PICK_UP_DROP_OFF_TYPE_PHONE
            elif drop_off_type == "3":
                drop_off_type = models.StopTime.PICK_UP_DROP_OFF_TYPE_COORDINATE_WITH_DRIVER
            else:
                raise ValueError(f"Invalid drop_off type: {drop_off_type}")

            k = (trip.pk, row["stop_sequence"])
            if k not in objs_k:
                objs_k.add(k)
                objs.append(models.StopTime(
                    trip=trip,
                    sequence=row["stop_sequence"],
                    stop=stop,
                    arrival_time=arrival_time,
                    departure_time=departure_time,
                    headsign=row.get("stop_headsign"),
                    distance_traveled=row.get("shape_dist_traveled"),
                    pick_up_type=pick_up_type,
                    drop_off_type=drop_off_type,
                ))
                if trip not in seen_ids:
                    seen_ids[trip] = []
                seen_ids[trip].append(row["stop_sequence"])
    models.StopTime.objects.bulk_create(
        objs,
        update_conflicts=True,
        unique_fields=("trip", "sequence"),
        update_fields=("stop", "arrival_time", "departure_time", "headsign", "distance_traveled", "pick_up_type", "drop_off_type"),
    )
    for t, sequences in seen_ids.items():
        models.StopTime.objects.filter(Q(trip=t) & ~Q(sequence__in=sequences)).delete()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def process_gtfs_rt(feed_id: str, feed_url: str):
    r = session.get(feed_url, headers={
        "User-Agent": "Zuegli (q@magicalcodewit.ch)"
    })
    r.raise_for_status()

    data = gtfs_rt_pb2.FeedMessage()
    if r.headers["Content-Type"].split(";", 1)[0] == "application/json":
        google.protobuf.json_format.Parse(r.text, data)
    else:
        raise ValueError("Unsupported Content-Type: {}".format(r.headers["Content-Type"]))

    if data.header.gtfs_realtime_version != "2.0":
        raise ValueError(f"Unsupported GTFS realtime version: {data.header.gtfs_realtime_version}")
    if data.header.incrementality != data.header.FULL_DATASET:
        raise ValueError(f"Unsupported incrementality: {data.header.incrementality}")

    generation_time = datetime.datetime.fromtimestamp(data.header.timestamp, tz=datetime.timezone.utc)
    with transaction.atomic():
        with django.db.connection.cursor() as dc:
            dc.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")
        if f := models.GtfsRtFeed.objects.filter(feed_id=feed_id).first():
            if f.last_updated >= generation_time:
                logger.info("Feed not updated since last fetch")
                return

            f.last_updated = generation_time
            f.save()
        else:
            f = models.GtfsRtFeed.objects.create(feed_id=feed_id, last_updated=generation_time)

        for entity in data.entity:
            if entity.HasField("trip_update"):
                if entity.trip_update.trip.schedule_relationship not in (
                    entity.trip_update.trip.SCHEDULED,
                    entity.trip_update.trip.CANCELED,
                ):
                    logger.warning(f"Unknown schedule relationship: {entity.trip_update.trip.schedule_relationship}")
                    continue

                trip = models.Trip.objects.filter(
                    trip_id=entity.trip_update.trip.trip_id,
                ).first()
                if not trip:
                    logger.warning(f"Unknown trip {entity.trip_update.trip.trip_id}")
                    continue

                trip_date = datetime.datetime.strptime(entity.trip_update.trip.start_date, "%Y%m%d").date()
                start_time = datetime.datetime.combine(trip_date, datetime.time(0, 0, 0))
                tu, _ = models.TripUpdate.objects.update_or_create(
                    rt_feed=f,
                    trip=trip,
                    date=trip_date,
                    defaults={
                        "cancelled": entity.trip_update.trip.schedule_relationship == entity.trip_update.trip.CANCELED,
                        "last_updated": datetime.datetime.fromtimestamp(entity.trip_update.timestamp, tz=datetime.timezone.utc),
                    }
                )

                objs = []
                for stop in entity.trip_update.stop_time_update:
                    stop_time = trip.stops.filter(sequence=stop.stop_sequence).first()
                    if not stop_time:
                        logger.warning(f"Unknown stop #{stop.stop_sequence} on trip {trip.trip_id}")
                        continue

                    su = models.StopUpdate(
                        trip_update=tu,
                        stop=stop_time,
                        skipped=stop.schedule_relationship == stop.SKIPPED
                    )

                    stop_tz = pytz.timezone(stop_time.stop.timezone)
                    if stop.HasField("arrival"):
                        if stop.arrival.time:
                            su.arrival = datetime.datetime.fromtimestamp(stop.arrival.time, tz=datetime.timezone.utc).astimezone(stop_tz)
                        if stop.arrival.delay is not None:
                            su.arrival = stop_tz.localize(start_time + datetime.timedelta(seconds=stop_time.arrival_time) + datetime.timedelta(seconds=stop.arrival.delay))
                    if stop.HasField("departure"):
                        if stop.departure.time:
                            su.departure = datetime.datetime.fromtimestamp(stop.departure.time, tz=datetime.timezone.utc).astimezone(stop_tz)
                        elif stop.departure.delay is not None:
                            su.departure = stop_tz.localize(start_time + datetime.timedelta(seconds=stop_time.departure_time) + datetime.timedelta(seconds=stop.departure.delay))

                    if stop.stop_time_properties:
                        if stop.stop_time_properties.assigned_stop_id:
                            su.assigned_stop = models.Stop.objects.get(feed_id=feed_id, stop_id=stop.stop_time_properties.assigned_stop_id)

                    objs.append(su)

                models.StopUpdate.objects.bulk_create(
                    objs,
                    update_conflicts=True,
                    unique_fields=("trip_update", "stop"),
                    update_fields=("skipped", "arrival", "departure", "assigned_stop"),
                )


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def process_all_gtfs():
    for feed_id, feed_url in data.GTFS_FEEDS.items():
        process_gtfs.delay(feed_id, feed_url)

@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def process_all_gtfs_rt():
    for feed_id, feed_url in data.GTFS_RT_FEEDS.items():
        process_gtfs_rt.delay(feed_id, feed_url)