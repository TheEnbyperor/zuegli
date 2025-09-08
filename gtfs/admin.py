from django.contrib import admin
from . import models


@admin.register(models.Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_filter = (
        "feed_id",
    )


@admin.register(models.Stop)
class StopAdmin(admin.ModelAdmin):
    list_filter = (
        "feed_id",
    )


@admin.register(models.Route)
class RouteAdmin(admin.ModelAdmin):
    list_filter = (
        "feed_id",
        "route_type"
    )
    search_fields = (
        "route_id",
        "short_name",
        "long_name"
    )


class CalendarExceptionInlineAdmin(admin.StackedInline):
    model = models.CalendarException
    extra = 0


@admin.register(models.Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_filter = (
        "feed_id",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday"
    )
    inlines = (CalendarExceptionInlineAdmin,)


@admin.register(models.CalendarException)
class CalendarExceptionAdmin(admin.ModelAdmin):
    list_filter = (
        "feed_id",
        "exception"
    )


class StopTimeAdmin(admin.StackedInline):
    model = models.StopTime
    extra = 0
    readonly_fields = (
        "arrival_time_str",
        "departure_time_str",
    )


@admin.register(models.Trip)
class TripAdmin(admin.ModelAdmin):
    list_filter = (
        "feed_id",
        "direction"
    )
    search_fields = (
        "trip_id",
        "headsign",
        "short_name",
        "block_id"
    )
    inlines = (StopTimeAdmin,)