import icalendar
import pytz
from django.conf import settings
from django.shortcuts import reverse
from . import models, templatetags


def supports_calendar(ticket: "models.Ticket") -> bool:
    ticket_instance = ticket.active_instance()
    if isinstance(ticket_instance, models.UICTicketInstance):
        ticket_data = ticket_instance.as_ticket()
        if ticket_data.flex:
            if len(ticket_data.flex.data["transportDocument"]) >= 1:
                ticket_document = next(map(
                    lambda d: d["ticket"][1],
                    filter(
                        lambda d: d["ticket"][0] == "openTicket", ticket_data.flex.data["transportDocument"]
                    ),
                ), None)
                if ticket_document:
                    if (
                            "fromStationNum" in ticket_document or "fromStationNameUTF8" in ticket_document or
                            "fromStationIA5" in ticket_document
                    ) and (
                            "toStationNum" in ticket_document or "toStationNameUTF8" in ticket_document or
                            "toStationIA5" in ticket_document
                    ):
                        return True

    return False


def make_calendar(ticket: "models.Ticket") -> bytes:
    cal = icalendar.Calendar()
    cal.add("version", "2.0")
    add_ticket_to_calendar(cal, ticket)
    return cal.to_ical()


def make_user_calendar(account: "models.Account") -> bytes:
    cal = icalendar.Calendar()
    cal.add("version", "2.0")
    for ticket in account.tickets.all():
        add_ticket_to_calendar(cal, ticket)
    return cal.to_ical()


def add_ticket_to_calendar(cal: icalendar.Calendar, ticket: "models.Ticket"):
    ticket_instance = ticket.active_instance()
    ticket_url = reverse('ticket', kwargs={"pk": ticket.pk})

    event = icalendar.Event()
    event.add("url", f"{settings.EXTERNAL_URL_BASE}{ticket_url}")
    event.add("status", "confirmed")

    if isinstance(ticket_instance, models.UICTicketInstance):
        ticket_data = ticket_instance.as_ticket()
        issued_at = ticket_data.issuing_time().astimezone(pytz.utc)
        if ticket_data.flex:

            ticket_document = next(map(
                lambda d: d["ticket"][1],
                filter(
                    lambda d: d["ticket"][0] == "openTicket", ticket_data.flex.data["transportDocument"]
                ),
            ), None)
            reservation_document = next(map(
                lambda d: d["ticket"][1],
                filter(
                    lambda d: d["ticket"][0] == "reservation", ticket_data.flex.data["transportDocument"]
                ),
            ), None)

            if reservation_document:
                ref = reservation_document.get("referenceIA5") or int(reservation_document.get("referenceNum", 0))
                event.add("uid", f"{ticket.public_id()}:{ref}")

                departure_time = templatetags.rics.rics_departure_time(reservation_document, issued_at)
                arrival_time = templatetags.rics.rics_arrival_time(reservation_document, issued_at)

                tz = departure_time.tzinfo
                tz_offset = tz.utcoffset(departure_time).seconds // 3600
                event.add("dtstart", icalendar.prop.vDatetime(departure_time.replace(tzinfo=None)), {
                    "TZID": f"Etc/GMT-{tz_offset}" if tz_offset > 0 else f"Etc/GMT+{-tz_offset}",
                })

                tz = arrival_time.tzinfo
                tz_offset = tz.utcoffset(arrival_time).seconds // 3600
                event.add("dtend", icalendar.prop.vDatetime(arrival_time.replace(tzinfo=None)), {
                    "TZID": f"Etc/GMT-{tz_offset}" if tz_offset > 0 else f"Etc/GMT+{-tz_offset}",
                })

                if "fromStationNameUTF8" in reservation_document:
                    from_station_name = reservation_document["fromStationNameUTF8"]
                elif "fromStationNameIA5" in reservation_document:
                    from_station_name = reservation_document["fromStationNameIA5"]
                else:
                    return

                event.add("location", from_station_name)

                if "toStationNameUTF8" in reservation_document:
                    to_station_name = reservation_document["toStationNameUTF8"]
                elif "toStationNameIA5" in reservation_document:
                    to_station_name = reservation_document["toStationNameIA5"]
                else:
                    return

                train_number = reservation_document.get("trainIA5") or str(reservation_document.get("trainNum", 0))
                if train_number and train_number != "0":
                    event.add("summary", f"{train_number}: {from_station_name} ➡ {to_station_name}")
                else:
                    event.add("summary", f"{from_station_name} ➡ {to_station_name}")

            elif ticket_document:
                ref = ticket_document.get("referenceIA5") or int(ticket_document.get("referenceNum", 0))
                event.add("uid", f"{ticket.public_id()}:{ref}")

                if "fromStationNum" in ticket_document:
                    from_station = templatetags.rics.get_station(ticket_document["fromStationNum"], ticket_document)
                else:
                    from_station = None
                if "toStationNum" in ticket_document:
                    to_station = templatetags.rics.get_station(ticket_document["toStationNum"], ticket_document)
                else:
                    to_station = None

                if from_station:
                    from_station_name = from_station["name"]
                    event.add("geo", (float(from_station["latitude"]), float(from_station["longitude"])))
                    event.add(
                        "X-APPLE-STRUCTURED-LOCATION",
                        icalendar.prop.vInline(f"geo:{from_station['latitude']},{from_station['longitude']}"),
                        {
                            "VALUE": "URI",
                            "X-APPLE-RADIUS": "0",
                            "X-TITLE": from_station["name"]
                        }
                    )
                elif "fromStationNameUTF8" in ticket_document:
                    from_station_name = ticket_document["fromStationNameUTF8"]
                elif "fromStationNameIA5" in ticket_document:
                    from_station_name = ticket_document["fromStationNameIA5"]
                else:
                    return

                event.add("location", from_station_name)

                if to_station:
                    to_station_name = to_station["name"]
                elif "toStationNameUTF8" in ticket_document:
                    to_station_name = ticket_document["toStationNameUTF8"]
                elif "toStationNameIA5" in ticket_document:
                    to_station_name = ticket_document["toStationNameIA5"]
                else:
                    return

                departure_time = None
                train_number = None
                if "validRegion" in ticket_document:
                    train_links = list(map(
                        lambda l: l[1],
                        filter(lambda l: l[0] == "trainLink", ticket_document["validRegion"])
                    ))
                    if train_links:
                        train_number = ", ".join(list(
                            dict.fromkeys([l.get("trainIA5") or str(l.get("trainNum")) for l in train_links])
                        ))
                        departure_time = templatetags.rics.rics_departure_time(train_links[0], issued_at)
                        tz = departure_time.tzinfo
                        tz_offset = tz.utcoffset(departure_time).seconds // 3600
                        event.add("dtstart", icalendar.prop.vDatetime(departure_time.replace(tzinfo=None)), {
                            "TZID": f"Etc/GMT-{tz_offset}" if tz_offset > 0 else f"Etc/GMT+{-tz_offset}",
                        })

                if not departure_time:
                    valid_from = templatetags.rics.rics_valid_from(ticket_document, issued_at)
                    valid_to = templatetags.rics.rics_valid_until(ticket_document, issued_at)

                    event.add("dtstart", icalendar.prop.vDate(valid_from.date()), {
                        "VALUE": "DATE"
                    })
                    event.add("dtend", icalendar.prop.vDate(valid_to.date()), {
                        "VALUE": "DATE"
                    })

                if train_number:
                    event.add("summary", f"{train_number}: {from_station_name} ➡ {to_station_name}")
                else:
                    event.add("summary", f"{from_station_name} ➡ {to_station_name}")
            else:
                return

    cal.add_component(event)