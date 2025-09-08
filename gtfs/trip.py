import dataclasses
import typing
import datetime
import pytz
from . import models

STATION_MAPPING = {
    "eil": {
        "st_pancras_international_station_area": "7015400",
        "amsterdam_centraal_station_area": "8400058"
    }
}

@dataclasses.dataclass
class Stop:
    arrival: datetime.datetime
    departure: datetime.datetime
    rt_arrival: datetime.datetime
    rt_departure: datetime.datetime
    stop_time: models.StopTime
    stop: models.Stop
    skipped: bool
    uic_station_id: typing.Optional[str]


@dataclasses.dataclass
class Trip:
    date: datetime.date
    trip: models.Trip
    stops: typing.List[Stop]
    cancelled: bool
    last_rt_data: typing.Optional[datetime.datetime] = None

    @classmethod
    def from_trip(cls, trip: models.Trip, date: datetime.date) -> "Trip":
        stops = []
        rt_info = models.TripUpdate.objects.filter(trip=trip).first()
        start_time = datetime.datetime.combine(date, datetime.time(0, 0, 0))
        for stop in trip.stops.all():
            stop_info = rt_info.stops.filter(stop=stop).first() if rt_info else None
            stop_tz = pytz.timezone(stop.stop.timezone)

            ps = stop.stop
            uic_station_id = None
            while ps:
                if ps.stop_id in STATION_MAPPING[ps.feed_id]:
                    uic_station_id = STATION_MAPPING[ps.feed_id][ps.stop_id]
                    break
                else:
                    ps = ps.parent_station

            stops.append(Stop(
                arrival=stop_tz.localize(start_time + datetime.timedelta(seconds=stop.arrival_time)) if stop.arrival_time else None,
                departure=stop_tz.localize(start_time + datetime.timedelta(seconds=stop.departure_time)) if stop.departure_time else None,
                stop_time=stop,
                stop=stop_info.assigned_stop or stop.stop if stop_info else stop.stop,
                rt_arrival=stop_info.arrival.astimezone(stop_tz) if stop_info and stop_info.arrival else None,
                rt_departure=stop_info.departure.astimezone(stop_tz) if stop_info and stop_info.departure else None,
                skipped=stop_info.skipped if stop_info else None,
                uic_station_id=uic_station_id,
            ))

        return cls(
            date=date,
            trip=trip,
            stops=stops,
            cancelled=rt_info.cancelled if rt_info else False,
            last_rt_data=rt_info.last_updated if rt_info else None,
        )