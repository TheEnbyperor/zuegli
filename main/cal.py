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

    if isinstance(ticket_instance, models.UICTicketInstance):
        ticket_data = ticket_instance.as_ticket()
        issued_at = ticket_data.issuing_time().astimezone(pytz.utc)
        if ticket_data.flex:
            for doc in ticket_data.flex.data["transportDocument"]:
                if doc["ticket"][0] == "openTicket":
                    ticket_document = doc["ticket"][1]
                    event = icalendar.Event()
                    event.add("url", f"{settings.EXTERNAL_URL_BASE}{ticket_url}")

                    ref = ticket_document.get("referenceIA5") or int(ticket_document.get("referenceNum", 0))
                    event.add("uid", f"{ticket.public_id()}:{ref}")
                    event.add("status", "confirmed")

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
                        continue

                    event.add("location", from_station_name)

                    if to_station:
                        to_station_name = to_station["name"]
                    elif "toStationNameUTF8" in ticket_document:
                        to_station_name = ticket_document["toStationNameUTF8"]
                    elif "toStationNameIA5" in ticket_document:
                        to_station_name = ticket_document["toStationNameIA5"]
                    else:
                        continue

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

                    if not departure_time:
                        departure_time = templatetags.rics.rics_valid_from(ticket_document, issued_at)

                    tz = departure_time.tzinfo
                    tz_offset = tz.utcoffset(departure_time).seconds // 3600
                    event.add("dtstart", icalendar.prop.vDatetime(departure_time.replace(tzinfo=None)), {
                        "TZID": f"Etc/GMT-{tz_offset}" if tz_offset > 0 else f"Etc/GMT+{-tz_offset}",
                    })

                    if train_number:
                        event.add("summary", f"{train_number}: {from_station_name} ➡ {to_station_name}")
                    else:
                        event.add("summary", f"{from_station_name} ➡ {to_station_name}")

                    cal.add_component(event)