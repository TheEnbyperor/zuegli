from django.db import models
from django.db.models import UniqueConstraint


class Agency(models.Model):
    feed_id = models.CharField(max_length=255, verbose_name="Feed ID")
    agency_id = models.CharField(max_length=255, verbose_name="Agency ID")
    name = models.CharField(max_length=255)
    url = models.URLField(verbose_name="URL")
    timezone = models.CharField(max_length=64)
    primary_language = models.CharField(max_length=64, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    fare_url = models.URLField(blank=True, null=True, verbose_name="Fare URL")
    email = models.EmailField(blank=True, null=True)

    class Meta:
        unique_together = (
            ("feed_id", "agency_id"),
        )
        verbose_name_plural = "Agencies"

    def __str__(self):
        return f"{self.feed_id}:{self.agency_id} ({self.name})"


class Stop(models.Model):
    LOCATION_TYPE_STOP = "stop"
    LOCATION_TYPE_STATION = "station"
    LOCATION_TYPE_ENTRANCE = "entrance"
    LOCATION_TYPE_GENERIC_NODE = "generic-node"
    LOCATION_TYPE_BOARDING_AREA = "boarding-area"
    LOCATION_TYPES = (
        (LOCATION_TYPE_STOP, "Stop"),
        (LOCATION_TYPE_STATION, "Station"),
        (LOCATION_TYPE_ENTRANCE, "Entrance/Exit"),
        (LOCATION_TYPE_GENERIC_NODE, "Generic Node"),
        (LOCATION_TYPE_BOARDING_AREA, "Boarding Area"),
    )

    feed_id = models.CharField(max_length=255, verbose_name="Feed ID")
    stop_id = models.CharField(max_length=255, verbose_name="Stop ID")
    code = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    tts_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    long = models.FloatField(blank=True, null=True)
    url = models.URLField(blank=True, null=True, verbose_name="URL")
    location_type = models.CharField(max_length=64, choices=LOCATION_TYPES)
    parent_station = models.ForeignKey("self", blank=True, null=True, on_delete=models.CASCADE)
    timezone = models.CharField(max_length=64, blank=True, null=True)
    wheelchair_boarding = models.BooleanField(blank=True, null=True)
    platform_code = models.CharField(max_length=255, blank=True, null=True)
    # TODO: level ID

    class Meta:
        unique_together = (
            ("feed_id", "stop_id"),
        )

    def __str__(self):
        return f"{self.feed_id}:{self.stop_id} ({self.name})"

class Route(models.Model):
    ROUTE_TYPE_LIGHT_RAIL = "light-rail"
    ROUTE_TYPE_METRO = "metro"
    ROUTE_TYPE_RAIL = "rail"
    ROUTE_TYPE_BUS = "bus"
    ROUTE_TYPE_FERRY = "ferry"
    ROUTE_TYPE_CABLE_TRAM = "cable-tram"
    ROUTE_TYPE_AERIAL_LIFT = "aerial-lift"
    ROUTE_TYPE_FUNICULAR = "funicular"
    ROUTE_TYPE_TROLLEYBUS = "trolleybus"
    ROUTE_TYPE_MONORAIL = "monorail"
    ROUTE_TYPES = (
        (ROUTE_TYPE_LIGHT_RAIL, "Tram/Light Rail"),
        (ROUTE_TYPE_METRO, "Metro/Subway"),
        (ROUTE_TYPE_RAIL, "Rail"),
        (ROUTE_TYPE_BUS, "Bus"),
        (ROUTE_TYPE_FERRY, "Ferry"),
        (ROUTE_TYPE_CABLE_TRAM, "Cable Tram"),
        (ROUTE_TYPE_AERIAL_LIFT, "Aerial Lift"),
        (ROUTE_TYPE_FUNICULAR, "Funicular"),
        (ROUTE_TYPE_TROLLEYBUS, "Trolleybus"),
        (ROUTE_TYPE_MONORAIL, "Monorail"),
    )

    feed_id = models.CharField(max_length=255, verbose_name="Feed ID")
    route_id = models.CharField(max_length=255, verbose_name="Route ID")
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    short_name = models.CharField(max_length=255, blank=True, null=True)
    long_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    route_type = models.CharField(max_length=64, choices=ROUTE_TYPES)
    url = models.URLField(blank=True, null=True, verbose_name="URL")
    colour = models.CharField(max_length=6, blank=True, null=True)
    text_colour = models.CharField(max_length=6, blank=True, null=True)
    sort_order = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        unique_together = (
            ("feed_id", "route_id"),
        )

    def __str__(self):
        return f"{self.feed_id}:{self.route_id} ({self.short_name})"


class Calendar(models.Model):
    feed_id = models.CharField(max_length=255, verbose_name="Feed ID")
    calendar_id = models.CharField(max_length=255, verbose_name="Calendar ID")
    monday = models.BooleanField(default=False, blank=True, verbose_name="Monday")
    tuesday = models.BooleanField(default=False, blank=True, verbose_name="Tuesday")
    wednesday = models.BooleanField(default=False, blank=True, verbose_name="Wednesday")
    thursday = models.BooleanField(default=False, blank=True, verbose_name="Thursday")
    friday = models.BooleanField(default=False, blank=True, verbose_name="Friday")
    saturday = models.BooleanField(default=False, blank=True, verbose_name="Saturday")
    sunday = models.BooleanField(default=False, blank=True, verbose_name="Sunday")
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        unique_together = (
            ("feed_id", "calendar_id"),
        )

    def __str__(self):
        return f"{self.feed_id}:{self.calendar_id}"


class CalendarException(models.Model):
    SERVICE_ADDED = "added"
    SERVICE_REMOVED = "removed"
    EXCEPTIONS = (
        (SERVICE_ADDED, "Service added"),
        (SERVICE_REMOVED, "Service removed"),
    )

    feed_id = models.CharField(max_length=255, verbose_name="Feed ID")
    calendar = models.ForeignKey("Calendar", on_delete=models.CASCADE, blank=True, null=True, related_name="exceptions")
    date = models.DateField()
    exception = models.CharField(max_length=64, choices=EXCEPTIONS)

    class Meta:
        unique_together = (
            ("feed_id", "calendar", "date"),
        )
        index_together = (
            ("feed_id", "calendar",),
        )

    def __str__(self):
        return f"{self.calendar}: {self.date}"


class CalendarDate(models.Model):
    feed_id = models.CharField(max_length=255, verbose_name="Feed ID")
    service_id = models.CharField(max_length=255, verbose_name="Calendar ID", blank=True, null=True)
    date = models.DateField()
    exception = models.CharField(max_length=64, choices=CalendarException.EXCEPTIONS)

    class Meta:
        unique_together = (
            ("feed_id", "service_id", "date"),
        )
        index_together = (
            ("feed_id", "service_id"),
            ("date", "exception"),
        )

    def __str__(self):
        return f"{self.feed_id}:{self.service_id}: {self.date}"


class Trip(models.Model):
    DIRECTION_UNSPECIFIED = "unspecified"
    DIRECTION_OUTBOUND = "outbound"
    DIRECTION_INBOUND = "inbound"
    DIRECTIONS = (
        (DIRECTION_UNSPECIFIED, "Unspecified"),
        (DIRECTION_OUTBOUND, "Outbound"),
        (DIRECTION_INBOUND, "Inbound"),
    )

    feed_id = models.CharField(max_length=255, verbose_name="Feed ID")
    trip_id = models.CharField(max_length=255, verbose_name="Trip ID")
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, blank=True, null=True)
    calendar_date = models.ForeignKey(CalendarDate, on_delete=models.CASCADE, blank=True, null=True)
    headsign = models.CharField(max_length=255, blank=True, null=True)
    short_name = models.CharField(max_length=255, blank=True, null=True)
    direction = models.CharField(max_length=64, choices=DIRECTIONS)
    block_id = models.CharField(max_length=255, blank=True, null=True)
    shape = models.ForeignKey("Shape", on_delete=models.SET_NULL, blank=True, null=True)
    wheelchair_accessible = models.BooleanField(blank=True, null=True)
    bikes_allowed = models.BooleanField(blank=True, null=True)
    cars_allowed = models.BooleanField(blank=True, null=True)

    class Meta:
        unique_together = (
            ("feed_id", "trip_id"),
        )

    def __str__(self):
        return f"{self.feed_id}:{self.trip_id} ({self.short_name})"


class StopTime(models.Model):
    PICK_UP_DROP_OFF_TYPE_REGULAR = "regular"
    PICK_UP_DROP_OFF_TYPE_FORBIDDEN = "forbidden"
    PICK_UP_DROP_OFF_TYPE_PHONE = "phone"
    PICK_UP_DROP_OFF_TYPE_COORDINATE_WITH_DRIVER = "coordinate-with-driver"
    PICK_UP_DROP_OFF_TYPES = (
        (PICK_UP_DROP_OFF_TYPE_REGULAR, "Regularly scheduled"),
        (PICK_UP_DROP_OFF_TYPE_FORBIDDEN, "Forbidden"),
        (PICK_UP_DROP_OFF_TYPE_PHONE, "Phone agency"),
        (PICK_UP_DROP_OFF_TYPE_COORDINATE_WITH_DRIVER, "Coordinate with driver"),
    )

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="stops")
    sequence = models.PositiveIntegerField(blank=True, null=True)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    arrival_time = models.PositiveIntegerField(blank=True, null=True)
    departure_time = models.PositiveIntegerField(blank=True, null=True)
    headsign = models.CharField(max_length=255, blank=True, null=True)
    distance_traveled = models.FloatField(blank=True, null=True)
    pick_up_type = models.CharField(max_length=255, choices=PICK_UP_DROP_OFF_TYPES)
    drop_off_type = models.CharField(max_length=255, choices=PICK_UP_DROP_OFF_TYPES)

    class Meta:
        unique_together = (
            ("trip", "sequence"),
        )
        ordering = ("sequence",)

    def arrival_time_str(self):
        if not self.arrival_time:
            return ""

        secs = self.arrival_time % 60
        mins = (self.arrival_time // 60) % 60
        hours = self.arrival_time // 60 // 60
        return f"{hours:02}:{mins:02}:{secs:02}"

    def departure_time_str(self):
        if not self.departure_time:
            return ""

        secs = self.departure_time % 60
        mins = (self.departure_time // 60) % 60
        hours = self.departure_time // 60 // 60
        return f"{hours:02}:{mins:02}:{secs:02}"

    arrival_time_str.short_description = "Arrival time"
    departure_time_str.short_description = "Departure time"

    def __str__(self):
        return f"{self.trip}: {self.sequence} ({self.stop})"


class Shape(models.Model):
    feed_id = models.CharField(max_length=255, verbose_name="Feed ID")
    shape_id = models.CharField(max_length=255, verbose_name="Shape ID")

    class Meta:
        unique_together = (
            ("feed_id", "shape_id"),
        )


class ShapePoint(models.Model):
    shape = models.ForeignKey(Shape, on_delete=models.CASCADE, related_name="points")
    lat = models.FloatField()
    lon = models.FloatField()
    sequence = models.PositiveIntegerField()

    class Meta:
        unique_together = (
            ("shape", "sequence"),
        )


class GtfsRtFeed(models.Model):
    feed_id = models.CharField(max_length=255, verbose_name="Feed ID")
    last_updated = models.DateTimeField()


class TripUpdate(models.Model):
    rt_feed = models.ForeignKey(GtfsRtFeed, related_name="trip_updates", on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="updates")
    date = models.DateField()
    cancelled = models.BooleanField(default=False, blank=True)
    last_updated = models.DateTimeField()


class StopUpdate(models.Model):
    trip_update = models.ForeignKey(TripUpdate, on_delete=models.CASCADE, related_name="stops")
    stop = models.ForeignKey(StopTime, on_delete=models.CASCADE)
    assigned_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, blank=True, null=True)
    arrival = models.DateTimeField(blank=True, null=True)
    departure = models.DateTimeField(blank=True, null=True)
    skipped = models.BooleanField(default=False, blank=True)