import datetime
import json
import urllib.parse
import pytz
import pymupdf
import io
import typing
import copy
from PIL import Image, ImageOps
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.http import HttpResponse
from django.core.files.storage import storages
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib import messages
from main import forms, models, ticket, pkpass, vdv, aztec, templatetags, apn, gwallet, rsp, elb, uic, ssb


def robots(request):
    with storages["staticfiles"].open("main/robots.txt") as f:
        return HttpResponse(f.read(), content_type="text/plain")

def index(request):
    ticket_bytes = None
    tickets = []
    error = None

    if request.method == "POST":
        if request.POST.get("type") == "scan":
            try:
                ticket_bytes = bytes.fromhex(request.POST.get("ticket_hex"))
            except ValueError:
                pass

            image_form = forms.TicketUploadForm()
        else:
            image_form = forms.TicketUploadForm(request.POST, request.FILES)
            if image_form.is_valid():
                ticket_file = image_form.cleaned_data["ticket"]
                if ticket_file.size > 16 * 1024 * 1024:
                    image_form.add_error("ticket", "The ticket must be less than 16MB")
                else:
                    if ticket_file.content_type != "application/pdf":
                        try:
                            ticket_bytes = aztec.decode(ticket_file.read())
                        except aztec.AztecError as e:
                            image_form.add_error("ticket", str(e))
                    else:
                        try:
                            pdf = pymupdf.open(stream=ticket_file.read(), filetype=ticket_file.content_type)
                        except RuntimeError as e:
                            image_form.add_error("ticket", f"Error opening PDF: {e}")
                        else:
                            for page_index in range(len(pdf)):
                                for pdf_image in pdf.get_page_images(page_index):
                                    pdf_image = pdf.extract_image(pdf_image[0])
                                    try:
                                        ticket_bytes = aztec.decode(pdf_image["image"])
                                        tickets.append(ticket_bytes)
                                    except aztec.AztecError:
                                        continue

                            if not tickets:
                                image_form.add_error("ticket", f"Failed to find any Aztec codes in the PDF")

    else:
        image_form = forms.TicketUploadForm()

    if not tickets and ticket_bytes:
        tickets = [ticket_bytes]

    if tickets:
        ticket_ids = []
        errors = []
        for tb in tickets:
            try:
                ticket_data = ticket.parse_ticket(
                    tb, request.user.account if request.user.is_authenticated else None
                )
            except ticket.TicketError as e:
                errors.append({
                    "title": e.title,
                    "message": e.message,
                    "exception": e.exception,
                    "ticket_contents": ticket_bytes.hex()
                })
            else:
                ticket_pk = ticket_data.pk()
                defaults = {
                    "ticket_type": ticket_data.type(),
                    "last_updated": timezone.now(),
                }
                if request.user.is_authenticated:
                    defaults["account"] = request.user.account
                ticket_obj, ticket_created = models.Ticket.objects.update_or_create(id=ticket_pk, defaults=defaults)
                request.session["ticket_updated"] = True
                request.session["ticket_created"] = ticket_created
                ticket.create_ticket_obj(ticket_obj, ticket_bytes, ticket_data)
                apn.notify_ticket(ticket_obj)
                gwallet.sync_ticket(ticket_obj)
                ticket_ids.append(ticket_obj.id)

        if ticket_ids:
            if len(ticket_ids) > 1:
                messages.info(request, f"{len(ticket_ids) - 1} other tickets have been added to your account")
            return redirect('ticket', pk=ticket_ids[0])
        elif errors:
            error = errors[0]

    return render(request, "main/index.html", {
        "image_form": image_form,
        "error": error,
    })


def view_ticket(request, pk):
    ticket_obj = get_object_or_404(models.Ticket, id=pk)
    gwallet_url = gwallet.create_jwt_link(ticket_obj)

    is_saarvv = False
    is_db_abo = False
    active_instance = ticket_obj.active_instance()
    if isinstance(active_instance, models.VDVTicketInstance):
        if active_instance.ticket_org_id == 6310:
            is_saarvv = True
        elif active_instance.ticket_org_id == 6061:
            is_db_abo = True
    elif isinstance(active_instance, models.UICTicketInstance):
        if active_instance.distributor_rics in (80, 1080):
            is_db_abo = True

    has_saarvv = ticket_obj.account and ticket_obj.account.is_saarvv_authenticated()
    has_db_abo = (ticket_obj.account and ticket_obj.account.is_db_authenticated()) or ticket_obj.db_subscription

    photo_upload_forms = {}
    if rsp_obj := ticket_obj.rsp_instances.first():
        td = rsp_obj.as_ticket()  # type: ticket.RSPTicket
        if isinstance(td.data, rsp.RailcardData):
            photo_upload_forms["first"] = {
                "name": td.data.passenger_1_name(),
            }
            if name := ticket_obj.photos.get("first"):
                photo_upload_forms["first"]["current"] = default_storage.url(name)
            if td.data.has_passenger_2():
                photo_upload_forms["second"] = {
                    "name": td.data.passenger_2_name(),
                    "current": ticket_obj.photos.get("second"),
                }

    if request.method == "POST":
        if "photo-upload" in request.POST:
            pi = request.POST["photo-upload"]
            if pi in photo_upload_forms:
                if "photo" in request.FILES:
                    file = request.FILES["photo"]
                    if file.size > 16 * 1024 * 1024:
                        photo_upload_forms[pi]["error"] = "The photo must be less than 16MB"
                    elif file.content_type not in ("image/jpeg", "image/png"):
                        photo_upload_forms[pi]["error"] = "The photo must be a JPEG or PNG"
                    else:
                        file_name = default_storage.save(file.name, file)
                        ticket_obj.photos[pi] = file_name
                        ticket_obj.save()
                        apn.notify_ticket(ticket_obj)
                        gwallet.sync_ticket(ticket_obj)

    return render(request, "main/ticket.html", {
        "ticket": ticket_obj,
        "ticket_updated": request.session.pop("ticket_updated", False),
        "ticket_created": request.session.pop("ticket_created", False),
        "gwallet_url": gwallet_url,
        "photo_upload_forms": photo_upload_forms,
        "is_saarvv": is_saarvv,
        "has_saarvv": has_saarvv,
        "is_db_abo": is_db_abo,
        "has_db_abo": has_db_abo,
    })


def pass_photo_thumbnail(ticket_obj: "models.Ticket", size, padding):
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    images = []
    for k in ("first", "second"):
        if img := ticket_obj.photos.get(k):
            with default_storage.open(img) as f:
                i = Image.open(f)
                ImageOps.exif_transpose(i, in_place=True)
                i.thumbnail(out.size, Image.Resampling.LANCZOS)
                images.append(i)

    total_width = sum((i.width + padding) for i in images)
    x = (out.width // 2) - (total_width // 2)
    for i in images:
        out.paste(i, (x + (padding // 2), (out.height - i.height) // 2))
        x += i.width + (padding // 2)

    return out


def pass_photo_banner(request, pk):
    ticket_obj = get_object_or_404(models.Ticket, id=pk)
    out = pass_photo_thumbnail(ticket_obj, (1000, 500), 50)
    out_bytes = io.BytesIO()
    out.save(out_bytes, format='PNG')
    return HttpResponse(out_bytes.getvalue(), content_type="image/png")


def add_pkp_img(pkp, img_name: str, pass_path: str):
    img_name, img_name_ext = img_name.rsplit(".", 1)
    pass_path, pass_path_ext = pass_path.rsplit(".", 1)
    storage = storages["staticfiles"]
    with storage.open(f"{img_name}.{img_name_ext}", "rb") as f:
        img_1x = f.read()
        pkp.add_file(f"{pass_path}.{pass_path_ext}", img_1x)
    try:
        with storage.open(f"{img_name}@2x.{img_name_ext}", "rb") as f:
            img_2x = f.read()
            pkp.add_file(f"{pass_path}@2x.{pass_path_ext}", img_2x)
    except FileNotFoundError:
        pass
    try:
        with storages["staticfiles"].open(f"{img_name}@3x.{img_name_ext}", "rb") as f:
            img_3x = f.read()
            pkp.add_file(f"{pass_path}@3x.{pass_path_ext}", img_3x)
    except FileNotFoundError:
        pass


def ticket_pkpass(request, pk):
    ticket_obj: models.Ticket = get_object_or_404(models.Ticket, id=pk)
    return make_pkpass(ticket_obj)


def make_pkpass_file(ticket_obj: "models.Ticket", part: typing.Optional[str] = None):
    pkp = pkpass.PKPass()
    have_logo = False

    pass_json = {
        "formatVersion": 1,
        "organizationName": settings.PKPASS_CONF["organization_name"],
        "passTypeIdentifier": settings.PKPASS_CONF["pass_type"],
        "teamIdentifier": settings.PKPASS_CONF["team_id"],
        "serialNumber": ticket_obj.pk,
        "groupingIdentifier": ticket_obj.pk,
        "description": ticket_obj.get_ticket_type_display(),
        "sharingProhibited": True,
        "backgroundColor": "rgb(255, 255, 255)",
        "labelColor": "rgb(75, 75, 75)",
        "foregroundColor": "rgb(0, 0, 0)",
        "locations": [],
        "webServiceURL": f"{settings.EXTERNAL_URL_BASE}/api/apple/",
        "authenticationToken": ticket_obj.pkpass_authentication_token,
        "semantics": {}
    }

    pass_type = "generic"
    pass_fields = {
        "headerFields": [],
        "primaryFields": [],
        "secondaryFields": [],
        "auxiliaryFields": [],
        "backFields": []
    }
    has_return = False
    return_pass_fields = {
        "headerFields": [],
        "primaryFields": [],
        "secondaryFields": [],
        "auxiliaryFields": [],
        "backFields": []
    }
    return_pass_type = "generic"
    return_pass_json = None

    ticket_instance = ticket_obj.active_instance()

    if isinstance(ticket_instance, models.UICTicketInstance):
        ticket_data: ticket.UICTicket = ticket_instance.as_ticket()
        issued_at = ticket_data.issuing_time().astimezone(pytz.utc)
        issuing_rics = ticket_data.issuing_rics()

        pass_json["barcodes"] = [{
            "format": "PKBarcodeFormatAztec",
            "message": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
            "messageEncoding": "iso-8859-1",
            "altText": ticket_data.ticket_id()
        }]

        if ticket_id := ticket_data.ticket_id():
            pass_fields["backFields"].append({
                "key": "ticket-id",
                "label": "ticket-id-label",
                "value": ticket_id,
                "semantics": {
                    "confirmationNumber": ticket_id
                }
            })

        if issuing_rics in RICS_LOGO:
            add_pkp_img(pkp, RICS_LOGO[issuing_rics], "logo.png")
            have_logo = True
        if issuing_rics in RICS_BG:
            pass_json["backgroundColor"] = RICS_BG[ticket_data.envelope.issuer_rics]
        if issuing_rics in RICS_FG:
            pass_json["foregroundColor"] = RICS_FG[ticket_data.envelope.issuer_rics]
        if issuing_rics in RICS_FG_SECONDARY:
            pass_json["labelColor"] = RICS_FG_SECONDARY[ticket_data.envelope.issuer_rics]

        parsed_layout = None
        if ticket_data.layout and ticket_data.layout.standard in ("RCT2", "RTC2"):
            parser = uic.rct2_parse.RCT2Parser()
            parser.read(ticket_data.layout)
            parsed_layout = parser.parse(issuing_rics)

        if ticket_data.flex:
            pass_json["voided"] = not ticket_data.flex.data["issuingDetail"]["activated"]

            if ticket_data.flex.data["issuingDetail"].get("issuerName") in UIC_NAME_LOGO:
                add_pkp_img(pkp, UIC_NAME_LOGO[ticket_data.flex.data["issuingDetail"]["issuerName"]], "logo.png")
                have_logo = True

            if len(ticket_data.flex.data["transportDocument"]) >= 1:
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
                customer_card_document = next(map(
                    lambda d: d["ticket"][1],
                    filter(
                        lambda d: d["ticket"][0] == "customerCard", ticket_data.flex.data["transportDocument"]
                    ),
                ), None)
                pass_document = next(map(
                    lambda d: d["ticket"][1],
                    filter(
                        lambda d: d["ticket"][0] == "pass", ticket_data.flex.data["transportDocument"]
                    ),
                ), None)
                if ticket_document or reservation_document:
                    if ticket_document:
                        validity_start = templatetags.rics.rics_valid_from(ticket_document, issued_at)
                        validity_end = templatetags.rics.rics_valid_until(ticket_document, issued_at)

                        pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                        if ticket_obj.ticket_type != ticket_obj.TYPE_DEUTCHLANDTICKET:
                            pass_json["relevantDate"] = validity_start.strftime("%Y-%m-%dT%H:%M:%SZ")

                        if "fromStationNum" in ticket_document and "toStationNum" in ticket_document:
                            pass_type = "boardingPass"
                            pass_fields["transitType"] = "PKTransitTypeTrain"

                            from_station = templatetags.rics.get_station(ticket_document["fromStationNum"], ticket_document)
                            to_station = templatetags.rics.get_station(ticket_document["toStationNum"], ticket_document)

                            if "classCode" in ticket_document and ticket_document["classCode"] != "notApplicable":
                                pass_fields["auxiliaryFields"].append({
                                    "key": "class-code",
                                    "label": "class-code-label",
                                    "value": f"class-code-{ticket_document['classCode']}-label",
                                })

                            if from_station:
                                pass_fields["primaryFields"].append({
                                    "key": "from-station",
                                    "label": "from-station-label",
                                    "value": from_station["name"],
                                    "semantics": {
                                        "departureLocation": {
                                            "latitude": float(from_station["latitude"]),
                                            "longitude": float(from_station["longitude"]),
                                        },
                                        "departureStationName": from_station["name"]
                                    }
                                })
                                maps_link = urllib.parse.urlencode({
                                    "q": from_station["name"],
                                    "ll": f"{from_station['latitude']},{from_station['longitude']}"
                                })
                                pass_fields["backFields"].append({
                                    "key": "from-station-back",
                                    "label": "from-station-label",
                                    "value": from_station["name"],
                                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{from_station['name']}</a>",
                                })
                            elif "fromStationNameUTF8" in ticket_document:
                                pass_fields["primaryFields"].append({
                                    "key": "from-station",
                                    "label": "from-station-label",
                                    "value": ticket_document["fromStationNameUTF8"],
                                    "semantics": {
                                        "departureStationName": ticket_document["fromStationNameUTF8"]
                                    }
                                })
                            elif "fromStationIA5" in ticket_document:
                                pass_fields["primaryFields"].append({
                                    "key": "from-station",
                                    "label": "from-station-label",
                                    "value": ticket_document["fromStationIA5"],
                                    "semantics": {
                                        "departureStationName": ticket_document["fromStationIA5"]
                                    }
                                })

                            if to_station:
                                pass_fields["primaryFields"].append({
                                    "key": "to-station",
                                    "label": "to-station-label",
                                    "value": to_station["name"],
                                    "semantics": {
                                        "destinationLocation": {
                                            "latitude": float(to_station["latitude"]),
                                            "longitude": float(to_station["longitude"]),
                                        },
                                        "destinationStationName": to_station["name"]
                                    }
                                })
                                maps_link = urllib.parse.urlencode({
                                    "q": to_station["name"],
                                    "ll": f"{to_station['latitude']},{to_station['longitude']}"
                                })
                                pass_fields["backFields"].append({
                                    "key": "to-station-back",
                                    "label": "to-station-label",
                                    "value": to_station["name"],
                                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{to_station['name']}</a>",
                                })
                            elif "toStationNameUTF8" in ticket_document:
                                pass_fields["primaryFields"].append({
                                    "key": "to-station",
                                    "label": "to-station-label",
                                    "value": ticket_document["toStationNameUTF8"],
                                    "semantics": {
                                        "destinationStationName": ticket_document["toStationNameUTF8"]
                                    }
                                })
                            elif "toStationIA5" in ticket_document:
                                pass_fields["primaryFields"].append({
                                    "key": "to-station",
                                    "label": "to-station-label",
                                    "value": ticket_document["toStationIA5"],
                                    "semantics": {
                                        "destinationStationName": ticket_document["toStationIA5"]
                                    }
                                })
                        else:
                            if "classCode" in ticket_document and ticket_document["classCode"] != "notApplicable":
                                pass_fields["auxiliaryFields"].append({
                                    "key": "class-code",
                                    "label": "class-code-label",
                                    "value": f"class-code-{ticket_document['classCode']}-label",
                                })

                        if len(ticket_document.get("tariffs", [])) >= 1:
                            tariff = ticket_document["tariffs"][0]
                            if "tariffDesc" in tariff:
                                pass_fields["headerFields"].append({
                                    "key": "product",
                                    "label": "product-label",
                                    "value": tariff["tariffDesc"]
                                })
                                pass_fields["backFields"].append({
                                    "key": "product-back",
                                    "label": "product-label",
                                    "value": tariff["tariffDesc"],
                                })

                            reduction_cards = ", ".join(list(map(lambda c: c["cardName"], tariff.get("reductionCard", []))))
                            if reduction_cards:
                                pass_fields["auxiliaryFields"].append({
                                    "key": f"reduction-card",
                                    "label": "reduction-card-label",
                                    "value": reduction_cards,
                                })

                        pass_fields["backFields"].append({
                            "key": "return-included",
                            "label": "return-included-label",
                            "value": "return-included-yes" if ticket_document["returnIncluded"] else "return-included-no",
                        })

                        if "productIdIA5" in ticket_document:
                            pass_fields["backFields"].append({
                                "key": "product-id",
                                "label": "product-id-label",
                                "value": ticket_document["productIdIA5"],
                            })

                        pass_fields["secondaryFields"].append({
                            "key": "validity-start",
                            "label": "validity-start-label",
                            "dateStyle": "PKDateStyleMedium",
                            "timeStyle": "PKDateStyleNone",
                            "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })
                        pass_fields["secondaryFields"].append({
                            "key": "validity-end",
                            "label": "validity-end-label",
                            "dateStyle": "PKDateStyleMedium",
                            "timeStyle": "PKDateStyleNone",
                            "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "changeMessage": "validity-end-change"
                        })

                        if "validRegionDesc" in ticket_document:
                            pass_fields["backFields"].append({
                                "key": "valid-region",
                                "label": "valid-region-label",
                                "value": ticket_document["validRegionDesc"],
                            })

                        if "validRegion" in ticket_document and ticket_document["validRegion"][0][0] == "trainLink":
                            train_links = list(map(lambda l: l[1], filter(lambda l: l[0] == "trainLink", ticket_document["validRegion"])))
                            departure_time = templatetags.rics.rics_departure_time(train_links[0], issued_at)
                            pass_json["relevantDate"] = departure_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                            train_number = ", ".join(list(dict.fromkeys([l.get("trainIA5") or str(l.get("trainNum")) for l in train_links])))
                            pass_fields["headerFields"] = [{
                                "key": "train-number",
                                "label": "train-number-label",
                                "value": train_number,
                                "semantics": {
                                    "vehicleNumber": train_number
                                }
                            }]
                            pass_fields["secondaryFields"] = list(filter(
                                lambda f: f["key"] not in ("validity-start", "validity-end"),
                                pass_fields["secondaryFields"]
                            ))
                            pass_fields["secondaryFields"].append({
                                "key": "departure-time",
                                "label": "departure-time-label",
                                "value": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "dateStyle": "PKDateStyleShort",
                                "timeStyle": "PKDateStyleShort",
                                "semantics": {
                                    "originalDepartureDate": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                }
                            })

                        if "returnDescription" in ticket_document:
                            return_document = ticket_document["returnDescription"]
                            has_return = True
                            return_pass_json = copy.deepcopy(pass_json)
                            return_pass_json["locations"] = []

                            return_pass_fields["headerFields"].extend(
                                filter(lambda f: f["key"] != "train-number", pass_fields["headerFields"]))
                            return_pass_fields["auxiliaryFields"].extend(pass_fields["auxiliaryFields"])
                            return_pass_fields["secondaryFields"].extend(
                                filter(lambda f: f["key"] != "departure-time", pass_fields["secondaryFields"]))
                            return_pass_fields["backFields"].extend(filter(
                                lambda f: f["key"] not in ("valid-region", "to-station-back", "from-station-back"),
                                pass_fields["backFields"]
                            ))

                            if "fromStationNum" in return_document and "toStationNum" in return_document:
                                return_pass_type = "boardingPass"
                                return_pass_fields["transitType"] = "PKTransitTypeTrain"

                                from_station = templatetags.rics.get_station(return_document["fromStationNum"], ticket_document)
                                to_station = templatetags.rics.get_station(return_document["toStationNum"], ticket_document)

                                if from_station:
                                    return_pass_fields["primaryFields"].append({
                                        "key": "from-station",
                                        "label": "from-station-label",
                                        "value": from_station["name"],
                                        "semantics": {
                                            "departureLocation": {
                                                "latitude": float(from_station["latitude"]),
                                                "longitude": float(from_station["longitude"]),
                                            },
                                            "departureStationName": from_station["name"]
                                        }
                                    })
                                    return_pass_json["locations"].append({
                                        "latitude": float(from_station["latitude"]),
                                        "longitude": float(from_station["longitude"]),
                                        "relevantText": from_station["name"]
                                    })
                                    maps_link = urllib.parse.urlencode({
                                        "q": from_station["name"],
                                        "ll": f"{from_station['latitude']},{from_station['longitude']}"
                                    })
                                    return_pass_fields["backFields"].append({
                                        "key": "from-station-back",
                                        "label": "from-station-label",
                                        "value": from_station["name"],
                                        "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{from_station['name']}</a>",
                                    })
                                elif "fromStationNameUTF8" in return_document:
                                    return_pass_fields["primaryFields"].append({
                                        "key": "from-station",
                                        "label": "from-station-label",
                                        "value": return_document["fromStationNameUTF8"],
                                        "semantics": {
                                            "departureStationName": return_document["fromStationNameUTF8"]
                                        }
                                    })
                                elif "fromStationIA5" in return_document:
                                    return_pass_fields["primaryFields"].append({
                                        "key": "from-station",
                                        "label": "from-station-label",
                                        "value": return_document["fromStationIA5"],
                                        "semantics": {
                                            "departureStationName": return_document["fromStationIA5"]
                                        }
                                    })

                                if to_station:
                                    return_pass_fields["primaryFields"].append({
                                        "key": "to-station",
                                        "label": "to-station-label",
                                        "value": to_station["name"],
                                        "semantics": {
                                            "destinationLocation": {
                                                "latitude": float(to_station["latitude"]),
                                                "longitude": float(to_station["longitude"]),
                                            },
                                            "destinationStationName": to_station["name"]
                                        }
                                    })
                                    return_pass_json["locations"].append({
                                        "latitude": float(to_station["latitude"]),
                                        "longitude": float(to_station["longitude"]),
                                        "relevantText": to_station["name"]
                                    })
                                    maps_link = urllib.parse.urlencode({
                                        "q": to_station["name"],
                                        "ll": f"{to_station['latitude']},{to_station['longitude']}"
                                    })
                                    return_pass_fields["backFields"].append({
                                        "key": "to-station-back",
                                        "label": "to-station-label",
                                        "value": to_station["name"],
                                        "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{to_station['name']}</a>",
                                    })
                                elif "toStationNameUTF8" in return_document:
                                    return_pass_fields["primaryFields"].append({
                                        "key": "to-station",
                                        "label": "to-station-label",
                                        "value": return_document["toStationNameUTF8"],
                                        "semantics": {
                                            "destinationStationName": return_document["toStationNameUTF8"]
                                        }
                                    })
                                elif "toStationIA5" in return_document:
                                    return_pass_fields["primaryFields"].append({
                                        "key": "to-station",
                                        "label": "to-station-label",
                                        "value": return_document["toStationIA5"],
                                        "semantics": {
                                            "destinationStationName": return_document["toStationIA5"]
                                        }
                                    })

                            if "validReturnRegionDesc" in return_document:
                                return_pass_fields["backFields"].append({
                                    "key": "valid-region",
                                    "label": "valid-region-label",
                                    "value": return_document["validReturnRegionDesc"],
                                })

                            if "validReturnRegion" in return_document and return_document["validReturnRegion"][0][0] == "trainLink":
                                train_link = return_document["validReturnRegion"][0][1]
                                departure_time = templatetags.rics.rics_departure_time(train_link, issued_at)
                                return_pass_json["relevantDate"] = departure_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                                train_number = train_link.get("trainIA5") or str(train_link.get("trainNum"))
                                return_pass_fields["headerFields"] = [{
                                    "key": "train-number",
                                    "label": "train-number-label",
                                    "value": train_number,
                                    "semantics": {
                                        "vehicleNumber": train_number
                                    }
                                }]
                                return_pass_json["locations"] = []
                                return_pass_fields["secondaryFields"].append({
                                    "key": "departure-time",
                                    "label": "departure-time-label",
                                    "value": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    "dateStyle": "PKDateStyleShort",
                                    "timeStyle": "PKDateStyleShort",
                                    "semantics": {
                                        "originalDepartureDate": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    }
                                })

                        pass_fields["backFields"].append({
                            "key": "validity-start-back",
                            "label": "validity-start-label",
                            "dateStyle": "PKDateStyleFull",
                            "timeStyle": "PKDateStyleFull",
                            "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })
                        return_pass_fields["backFields"].append({
                            "key": "validity-start-back",
                            "label": "validity-start-label",
                            "dateStyle": "PKDateStyleFull",
                            "timeStyle": "PKDateStyleFull",
                            "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })
                        pass_fields["backFields"].append({
                            "key": "validity-end-back",
                            "label": "validity-end-label",
                            "dateStyle": "PKDateStyleFull",
                            "timeStyle": "PKDateStyleFull",
                            "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })
                        return_pass_fields["backFields"].append({
                            "key": "validity-end-back",
                            "label": "validity-end-label",
                            "dateStyle": "PKDateStyleFull",
                            "timeStyle": "PKDateStyleFull",
                            "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })

                    if reservation_document:
                        pass_type = "boardingPass"
                        pass_fields["transitType"] = "PKTransitTypeTrain"

                        departure_time = templatetags.rics.rics_departure_time(reservation_document, issued_at)
                        arrival_time = templatetags.rics.rics_arrival_time(reservation_document, issued_at)
                        pass_json["relevantDate"] = departure_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                        if not ticket_document:
                            pass_json["expirationDate"] = arrival_time.strftime("%Y-%m-%dT%H:%M:%SZ")

                            if "fromStationNum" in reservation_document:
                                from_station = templatetags.rics.get_station(reservation_document["fromStationNum"], reservation_document)
                            else:
                                from_station = None

                            if "toStationNum" in reservation_document:
                                to_station = templatetags.rics.get_station(reservation_document["toStationNum"], reservation_document)
                            else:
                                to_station = None

                            if from_station:
                                pass_fields["primaryFields"].append({
                                    "key": "from-station",
                                    "label": "from-station-label",
                                    "value": from_station["name"],
                                    "semantics": {
                                        "departureLocation": {
                                            "latitude": float(from_station["latitude"]),
                                            "longitude": float(from_station["longitude"]),
                                        },
                                        "departureStationName": from_station["name"],
                                        "originalDepartureDate": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    }
                                })
                                maps_link = urllib.parse.urlencode({
                                    "q": from_station["name"],
                                    "ll": f"{from_station['latitude']},{from_station['longitude']}"
                                })
                                pass_fields["backFields"].append({
                                    "key": "from-station-back",
                                    "label": "from-station-label",
                                    "value": from_station["name"],
                                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{from_station['name']}</a>",
                                })
                            elif "fromStationNameUTF8" in reservation_document:
                                pass_fields["primaryFields"].append({
                                    "key": "from-station",
                                    "label": "from-station-label",
                                    "value": reservation_document["fromStationNameUTF8"],
                                    "semantics": {
                                        "departureStationName": reservation_document["fromStationNameUTF8"],
                                        "originalDepartureDate": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    }
                                })
                            elif "fromStationIA5" in reservation_document:
                                pass_fields["primaryFields"].append({
                                    "key": "from-station",
                                    "label": "from-station-label",
                                    "value": reservation_document["fromStationIA5"],
                                    "semantics": {
                                        "departureStationName": reservation_document["fromStationIA5"],
                                        "originalDepartureDate": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    }
                                })

                            if to_station:
                                pass_fields["primaryFields"].append({
                                    "key": "to-station",
                                    "label": "to-station-label",
                                    "value": to_station["name"],
                                    "semantics": {
                                        "destinationLocation": {
                                            "latitude": float(to_station["latitude"]),
                                            "longitude": float(to_station["longitude"]),
                                        },
                                        "destinationStationName": to_station["name"],
                                        "originalArrivalDate": arrival_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    }
                                })
                                maps_link = urllib.parse.urlencode({
                                    "q": to_station["name"],
                                    "ll": f"{to_station['latitude']},{to_station['longitude']}"
                                })
                                pass_fields["backFields"].append({
                                    "key": "to-station-back",
                                    "label": "to-station-label",
                                    "value": to_station["name"],
                                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{to_station['name']}</a>",
                                })
                            elif "toStationNameUTF8" in reservation_document:
                                pass_fields["primaryFields"].append({
                                    "key": "to-station",
                                    "label": "to-station-label",
                                    "value": reservation_document["toStationNameUTF8"],
                                    "semantics": {
                                        "destinationStationName": reservation_document["toStationNameUTF8"],
                                        "originalArrivalDate": arrival_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    }
                                })
                            elif "toStationIA5" in reservation_document:
                                pass_fields["primaryFields"].append({
                                    "key": "to-station",
                                    "label": "to-station-label",
                                    "value": reservation_document["toStationIA5"],
                                    "semantics": {
                                        "destinationStationName": reservation_document["toStationIA5"],
                                        "originalArrivalDate": arrival_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    }
                                })

                            if "classCode" in reservation_document and reservation_document["classCode"] != "notApplicable":
                                pass_fields["auxiliaryFields"].append({
                                    "key": "class-code",
                                    "label": "class-code-label",
                                    "value": f"class-code-{reservation_document['classCode']}-label",
                                })

                        if "places" in reservation_document:
                            if "coach" in reservation_document["places"]:
                                pass_fields["auxiliaryFields"].append({
                                    "key": f"reservation-coach",
                                    "label": "coach-number-label",
                                    "value": reservation_document["places"]["coach"],
                                })
                            if "placeString" in reservation_document["places"]:
                                pass_fields["auxiliaryFields"].append({
                                    "key": f"reservation-seat",
                                    "label": "seat-number-label",
                                    "value": reservation_document["places"]["placeString"],
                                })
                            elif "placeNum" in reservation_document["places"]:
                                pass_fields["auxiliaryFields"].append({
                                    "key": f"reservation-seat",
                                    "label": "seat-number-label",
                                    "value": ", ".join(list(map(str, reservation_document["places"]["placeNum"]))),
                                })

                        pass_fields["secondaryFields"] = []
                        pass_fields["secondaryFields"].append({
                            "key": "departure-time",
                            "label": "departure-time-label",
                            "dateStyle": "PKDateStyleMedium",
                            "timeStyle": "PKDateStyleMedium",
                            "value": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })
                        pass_fields["secondaryFields"].append({
                            "key": "arrival-time",
                            "label": "arrival-time-label",
                            "dateStyle": "PKDateStyleMedium",
                            "timeStyle": "PKDateStyleMedium",
                            "value": arrival_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })
                        pass_fields["backFields"].append({
                            "key": "departure-time-back",
                            "label": "departure-time-label",
                            "dateStyle": "PKDateStyleFull",
                            "timeStyle": "PKDateStyleFull",
                            "value": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })
                        pass_fields["backFields"].append({
                            "key": "arrival-time-back",
                            "label": "arrival-time-label",
                            "dateStyle": "PKDateStyleFull",
                            "timeStyle": "PKDateStyleFull",
                            "value": arrival_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })

                        if not ticket_document:
                            for i, carrier_id in enumerate(reservation_document.get("carrierNum", [])):
                                if carrier := uic.rics.get_rics(carrier_id):
                                    if carrier["url"]:
                                        pass_fields["backFields"].append({
                                            "key": f"carrier-{i}",
                                            "label": "carrier-label",
                                            "value": carrier["full_name"],
                                            "attributedValue": f"<a href=\"{carrier['url']}\">{carrier['full_name']}</a>",
                                        })
                                    else:
                                        pass_fields["backFields"].append({
                                            "key": f"carrier-{i}",
                                            "label": "carrier-label",
                                            "value": carrier["full_name"],
                                        })
                                else:
                                    pass_fields["backFields"].append({
                                        "key": f"carrier-{i}",
                                        "label": "carrier-label",
                                        "value": str(carrier_id),
                                    })

                        train_number = reservation_document.get("trainIA5") or reservation_document.get("trainNum")
                        if train_number:
                            pass_fields["headerFields"] = [{
                                "key": "train-number",
                                "label": "train-number-label",
                                "value": str(train_number),
                                "semantics": {
                                    "vehicleNumber": str(train_number)
                                }
                            }]

                        if "referenceNum" in reservation_document:
                            pass_fields["backFields"].append({
                                "key": "reference-num",
                                "label": "reference-num-label",
                                "value": str(reservation_document["referenceNum"])
                            })

                elif customer_card_document:
                    validity_start = templatetags.rics.rics_valid_from_date(customer_card_document)
                    validity_end = templatetags.rics.rics_valid_until_date(customer_card_document)

                    if "cardTypeDescr" in customer_card_document:
                        pass_fields["backFields"].append({
                            "key": "product-back",
                            "label": "product-label",
                            "value": customer_card_document["cardTypeDescr"]
                        })

                        if customer_card_document["cardTypeDescr"] in BC_STRIP_IMG:
                            pass_type = "storeCard"
                            add_pkp_img(pkp, BC_STRIP_IMG[customer_card_document["cardTypeDescr"]], "strip.png")

                        pass_fields["headerFields"].append({
                            "key": "product",
                            "label": "product-label",
                            "value": customer_card_document["cardTypeDescr"]
                        })

                    if "cardIdIA5" in customer_card_document:
                        pass_fields["secondaryFields"].append({
                            "key": "card-id",
                            "label": "card-id-label",
                            "value": customer_card_document["cardIdIA5"],
                        })
                    elif "cardIdNum" in customer_card_document:
                        pass_fields["secondaryFields"].append({
                            "key": "card-id",
                            "label": "card-id-label",
                            "value": str(customer_card_document["cardIdNum"]),
                        })

                    if "classCode" in customer_card_document and customer_card_document["classCode"] != "notApplicable":
                        pass_fields["secondaryFields"].append({
                            "key": "class-code",
                            "label": "class-code-label",
                            "value": f"class-code-{customer_card_document['classCode']}-label",
                        })

                    if validity_start:
                        pass_fields["backFields"].append({
                            "key": "validity-start-back",
                            "label": "validity-start-label",
                            "dateStyle": "PKDateStyleFull",
                            "timeStyle": "PKDateStyleNone",
                            "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })
                    if validity_end:
                        pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                        pass_fields["backFields"].append({
                            "key": "validity-end-back",
                            "label": "validity-end-label",
                            "dateStyle": "PKDateStyleFull",
                            "timeStyle": "PKDateStyleNone",
                            "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })

                elif pass_document:
                    validity_start = templatetags.rics.rics_valid_from(pass_document, issued_at)
                    validity_end = templatetags.rics.rics_valid_until(pass_document, issued_at)

                    pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")

                    if "passType" in pass_document:
                        if pass_document["passType"] == 1:
                            product_name = "Eurail Global Pass"
                        elif pass_document["passType"] == 2:
                            product_name = "Interrail Global Pass"
                        elif pass_document["passType"] == 3:
                            product_name = "Interrail One Country Pass"
                        elif pass_document["passType"] == 4:
                            product_name = "Eurail One Country Pass"
                        elif pass_document["passType"] == 5:
                            product_name = "Eurail/Interrail Emergency ticket"
                        else:
                            product_name = f"Pass type {pass_document['passType']}"
                    elif "passDescription" in pass_document:
                        product_name = pass_document["passDescription"]
                    else:
                        product_name = None

                    if product_name:
                        pass_fields["headerFields"].append({
                            "key": "product",
                            "label": "product-label",
                            "value": product_name
                        })
                        pass_fields["backFields"].append({
                            "key": "product-back",
                            "label": "product-label",
                            "value": product_name,
                        })

                    pass_fields["secondaryFields"].append({
                        "key": "validity-start",
                        "label": "validity-start-label",
                        "dateStyle": "PKDateStyleMedium",
                        "timeStyle": "PKDateStyleNone",
                        "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })
                    pass_fields["secondaryFields"].append({
                        "key": "validity-end",
                        "label": "validity-end-label",
                        "dateStyle": "PKDateStyleMedium",
                        "timeStyle": "PKDateStyleNone",
                        "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "changeMessage": "validity-end-change"
                    })
                    pass_fields["backFields"].append({
                        "key": "validity-start-back",
                        "label": "validity-start-label",
                        "dateStyle": "PKDateStyleFull",
                        "timeStyle": "PKDateStyleFull",
                        "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })
                    pass_fields["backFields"].append({
                        "key": "validity-end-back",
                        "label": "validity-end-label",
                        "dateStyle": "PKDateStyleFull",
                        "timeStyle": "PKDateStyleFull",
                        "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })

            if len(ticket_data.flex.data.get("travelerDetail", {}).get("traveler", [])) >= 1:
                passenger = ticket_data.flex.data["travelerDetail"]["traveler"][0]
                first_name = passenger.get('firstName', "").strip()
                last_name = passenger.get('lastName', "").strip()

                if first_name or last_name:
                    field_data = {
                        "key": "passenger",
                        "label": "passenger-label",
                        "value": f"{first_name}\n{last_name}" if pass_type == "generic" else f"{first_name} {last_name}",
                        "semantics": {
                            "passengerName": {
                                "familyName": last_name,
                                "givenName": first_name,
                            }
                        }
                    }
                    if pass_type == "generic":
                        pass_fields["primaryFields"].append(field_data)
                        return_pass_fields["primaryFields"].append(field_data)
                    elif pass_type == "storeCard":
                        pass_fields["secondaryFields"].append(field_data)
                        return_pass_fields["secondaryFields"].append(field_data)
                    else:
                        pass_fields["auxiliaryFields"].append(field_data)
                        return_pass_fields["auxiliaryFields"].append(field_data)

                dob = templatetags.rics.rics_traveler_dob(passenger)
                if dob:
                    dob = datetime.datetime.combine(dob, datetime.time.min)
                    dob_field = {
                        "key": "date-of-birth",
                        "label": "date-of-birth-label",
                        "dateStyle": "PKDateStyleMedium",
                        "value": dob.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                    pass_fields["secondaryFields"].append(dob_field)
                    return_pass_fields["secondaryFields"].append(dob_field)
                else:
                    dob_year = passenger.get("yearOfBirth", 0)
                    dob_month = passenger.get("monthOfBirth", 0)
                    if dob_year != 0 and dob_month != 0:
                        pass_fields["secondaryFields"].append({
                            "key": "month-of-birth",
                            "label": "month-of-birth-label",
                            "value": f"{dob_month:02d}.{dob_year:04d}",
                        })
                        return_pass_fields["secondaryFields"].append({
                            "key": "month-of-birth",
                            "label": "month-of-birth-label",
                            "value": f"{dob_month:02d}.{dob_year:04d}",
                        })
                    elif dob_year != 0:
                        pass_fields["secondaryFields"].append({
                            "key": "year-of-birth",
                            "label": "year-of-birth-label",
                            "value": f"{dob_year:04d}",
                        })
                        return_pass_fields["secondaryFields"].append({
                            "key": "year-of-birth",
                            "label": "year-of-birth-label",
                            "value": f"{dob_year:04d}",
                        })

                if "countryOfResidence" in passenger:
                    pass_fields["secondaryFields"].append({
                        "key": "country-of-residence",
                        "label": "country-of-residence-label",
                        "value": templatetags.rics.get_country(passenger["countryOfResidence"]),
                    })
                    return_pass_fields["secondaryFields"].append({
                        "key": "country-of-residence",
                        "label": "country-of-residence-label",
                        "value": templatetags.rics.get_country(passenger["countryOfResidence"]),
                    })

                if "passportId" in passenger:
                    pass_fields["secondaryFields"].append({
                        "key": "passport-number",
                        "label": "passport-number-label",
                        "value": passenger["passportId"],
                    })
                    return_pass_fields["secondaryFields"].append({
                        "key": "passport-number",
                        "label": "passport-number-label",
                        "value": passenger["passportId"],
                    })

        elif ticket_data.db_bl:
            tz = pytz.timezone("Europe/Berlin")
            if ticket_data.db_bl.product:
                pass_fields["headerFields"].append({
                    "key": "product",
                    "label": "product-label",
                    "value": ticket_data.db_bl.product,
                })
                pass_fields["backFields"].append({
                    "key": "product-back",
                    "label": "product-label",
                    "value": ticket_data.db_bl.product,
                })

            if ticket_data.db_bl.from_station_uic and ticket_data.db_bl.to_station_uic:
                pass_type = "boardingPass"
                pass_fields["transitType"] = "PKTransitTypeTrain"

                from_station = templatetags.rics.get_station(ticket_data.db_bl.from_station_uic, "db")
                to_station = templatetags.rics.get_station(ticket_data.db_bl.to_station_uic, "db")

                if from_station:
                    pass_fields["primaryFields"].append({
                        "key": "from-station",
                        "label": "from-station-label",
                        "value": from_station["name"],
                        "semantics": {
                            "departureLocation": {
                                "latitude": float(from_station["latitude"]),
                                "longitude": float(from_station["longitude"]),
                            },
                            "departureStationName": from_station["name"]
                        }
                    })
                    pass_json["locations"].append({
                        "latitude": float(from_station["latitude"]),
                        "longitude": float(from_station["longitude"]),
                        "relevantText": from_station["name"]
                    })
                    maps_link = urllib.parse.urlencode({
                        "q": from_station["name"],
                        "ll": f"{from_station['latitude']},{from_station['longitude']}"
                    })
                    pass_fields["backFields"].append({
                        "key": "from-station-back",
                        "label": "from-station-label",
                        "value": from_station["name"],
                        "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{from_station['name']}</a>",
                    })
                elif ticket_data.db_bl.from_station_name:
                    pass_fields["primaryFields"].append({
                        "key": "from-station",
                        "label": "from-station-label",
                        "value": ticket_data.db_bl.from_station_name,
                        "semantics": {
                            "departureStationName": ticket_data.db_bl.from_station_name
                        }
                    })

                if to_station:
                    pass_fields["primaryFields"].append({
                        "key": "to-station",
                        "label": "to-station-label",
                        "value": to_station["name"],
                        "semantics": {
                            "destinationLocation": {
                                "latitude": float(from_station["latitude"]),
                                "longitude": float(from_station["longitude"]),
                            },
                            "destinationStationName": to_station["name"]
                        }
                    })
                    pass_json["locations"].append({
                        "latitude": float(to_station["latitude"]),
                        "longitude": float(to_station["longitude"]),
                        "relevantText": to_station["name"]
                    })
                    maps_link = urllib.parse.urlencode({
                        "q": to_station["name"],
                        "ll": f"{to_station['latitude']},{to_station['longitude']}"
                    })
                    pass_fields["backFields"].append({
                        "key": "to-station-back",
                        "label": "to-station-label",
                        "value": to_station["name"],
                        "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{to_station['name']}</a>",
                    })
                elif ticket_data.db_bl.to_station_name:
                    pass_fields["primaryFields"].append({
                        "key": "to-station",
                        "label": "to-station-label",
                        "value": ticket_data.db_bl.to_station_name,
                        "semantics": {
                            "destinationStationName": ticket_data.db_bl.to_station_name
                        }
                    })
            elif parsed_layout and len(parsed_layout.trips) and \
                    (parsed_layout.trips[0].departure_station or parsed_layout.trips[0].arrival_station):
                pass_type = "boardingPass"
                pass_fields["transitType"] = "PKTransitTypeTrain"

                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": parsed_layout.trips[0].departure_station,
                    "semantics": {
                        "departureStationName": parsed_layout.trips[0].departure_station
                    }
                })
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": parsed_layout.trips[0].arrival_station,
                    "semantics": {
                        "departureStationName": parsed_layout.trips[0].arrival_station,
                    }
                })


            if ticket_data.db_bl.service_class:
                if pass_type == "boardingPass":
                    pass_fields["auxiliaryFields"].append({
                        "key": "class-code",
                        "label": "class-code-label",
                        "value": f"class-code-{ticket_data.db_bl.service_class}-label",
                    })
                else:
                    pass_fields["headerFields"].append({
                        "key": "class-code",
                        "label": "class-code-label",
                        "value": f"class-code-{ticket_data.db_bl.service_class}-label",
                    })
            elif parsed_layout and parsed_layout.travel_class:
                if pass_type == "boardingPass":
                    pass_fields["auxiliaryFields"].append({
                        "key": "class-code",
                        "label": "class-code-label",
                        "value": parsed_layout.travel_class,
                    })
                else:
                    pass_fields["headerFields"].append({
                        "key": "class-code",
                        "label": "class-code-label",
                        "value": parsed_layout.travel_class,
                    })


            if ticket_data.db_bl.validity_start:
                validity_start = tz.localize(
                    datetime.datetime.combine(ticket_data.db_bl.validity_start, datetime.time.min)) \
                    .astimezone(pytz.utc)
                pass_json["relevantDate"] = validity_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                pass_fields["secondaryFields"].append({
                    "key": "validity-start",
                    "label": "validity-start-label",
                    "dateStyle": "PKDateStyleMedium",
                    "timeStyle": "PKDateStyleNone",
                    "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
                pass_fields["backFields"].append({
                    "key": "validity-start-back",
                    "label": "validity-start-label",
                    "dateStyle": "PKDateStyleFull",
                    "timeStyle": "PKDateStyleFull",
                    "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })

            if ticket_data.db_bl.validity_end:
                validity_end = tz.localize(datetime.datetime.combine(ticket_data.db_bl.validity_end, datetime.time.max)) \
                    .astimezone(pytz.utc)
                pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                pass_fields["secondaryFields"].append({
                    "key": "validity-end",
                    "label": "validity-end-label",
                    "dateStyle": "PKDateStyleMedium",
                    "timeStyle": "PKDateStyleNone",
                    "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "changeMessage": "validity-end-change"
                })
                pass_fields["backFields"].append({
                    "key": "validity-end-back",
                    "label": "validity-end-label",
                    "dateStyle": "PKDateStyleFull",
                    "timeStyle": "PKDateStyleFull",
                    "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })

            if ticket_data.db_bl.route:
                pass_fields["backFields"].append({
                    "key": "valid-region",
                    "label": "valid-region-label",
                    "value": ticket_data.db_bl.route,
                })
            elif parsed_layout and parsed_layout.train_data:
                pass_fields["backFields"].append({
                    "key": "train-data",
                    "label": "train-number-label",
                    "value": parsed_layout.train_data,
                })

            if ticket_data.db_bl.traveller_forename or ticket_data.db_bl.traveller_surname:
                field_data = {
                    "key": "passenger",
                    "label": "passenger-label",
                    "value": f"{ticket_data.db_bl.traveller_forename}\n{ticket_data.db_bl.traveller_surname}"
                    if pass_type == "generic" else
                    f"{ticket_data.db_bl.traveller_forename} {ticket_data.db_bl.traveller_surname}",
                    "semantics": {
                        "passengerName": {
                            "familyName": ticket_data.db_bl.traveller_surname,
                            "givenName": ticket_data.db_bl.traveller_forename,
                        }
                    }
                }
                if pass_type == "generic":
                    pass_fields["primaryFields"].append(field_data)
                else:
                    pass_fields["auxiliaryFields"].append(field_data)

        elif ticket_data.cd_ut:
            if parsed_layout and (parsed_layout.trips[0].departure_station or parsed_layout.trips[0].arrival_station):
                pass_type = "boardingPass"
                pass_fields["transitType"] = "PKTransitTypeTrain"

                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": parsed_layout.trips[0].departure_station,
                    "semantics": {
                        "departureStationName": parsed_layout.trips[0].departure_station
                    }
                })
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": parsed_layout.trips[0].arrival_station,
                    "semantics": {
                        "departureStationName": parsed_layout.trips[0].arrival_station,
                    }
                })

            if parsed_layout and parsed_layout.travel_class:
                if pass_type == "boardingPass":
                    pass_fields["auxiliaryFields"].append({
                        "key": "class-code",
                        "label": "class-code-label",
                        "value": parsed_layout.travel_class,
                    })
                else:
                    pass_fields["headerFields"].append({
                        "key": "class-code",
                        "label": "class-code-label",
                        "value": parsed_layout.travel_class,
                    })

            for res in ticket_data.cd_ut.reservations:
                pass_fields["headerFields"].append({
                    "key": "train-number",
                    "label": "train-number-label",
                    "value": res.train,
                })
                pass_fields["auxiliaryFields"].append({
                    "key": f"reservation-coach",
                    "label": "coach-number-label",
                    "value": res.carriage,
                })
                pass_fields["auxiliaryFields"].append({
                    "key": f"reservation-seat",
                    "label": "seat-number-label",
                    "value": res.seat,
                })

            if ticket_data.cd_ut.validity_start:
                pass_json["relevantDate"] = ticket_data.cd_ut.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                pass_fields["secondaryFields"].append({
                    "key": "validity-start",
                    "label": "validity-start-label",
                    "dateStyle": "PKDateStyleMedium",
                    "timeStyle": "PKDateStyleNone",
                    "value": ticket_data.cd_ut.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
                pass_fields["backFields"].append({
                    "key": "validity-start-back",
                    "label": "validity-start-label",
                    "dateStyle": "PKDateStyleFull",
                    "timeStyle": "PKDateStyleFull",
                    "value": ticket_data.cd_ut.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })

            if ticket_data.cd_ut.validity_end:
                pass_json["expirationDate"] = ticket_data.cd_ut.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                pass_fields["secondaryFields"].append({
                    "key": "validity-end",
                    "label": "validity-end-label",
                    "dateStyle": "PKDateStyleMedium",
                    "timeStyle": "PKDateStyleNone",
                    "value": ticket_data.cd_ut.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "changeMessage": "validity-end-change"
                })
                pass_fields["backFields"].append({
                    "key": "validity-end-back",
                    "label": "validity-end-label",
                    "dateStyle": "PKDateStyleFull",
                    "timeStyle": "PKDateStyleFull",
                    "value": ticket_data.cd_ut.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })

            if ticket_data.cd_ut.name:
                if pass_type == "boardingPass":
                    pass_fields["secondaryFields"].append({
                        "key": "passenger",
                        "label": "passenger-label",
                        "value": ticket_data.cd_ut.name,
                    })
                else:
                    pass_fields["primaryFields"].append({
                        "key": "passenger",
                        "label": "passenger-label",
                        "value": ticket_data.cd_ut.name,
                    })

        elif ticket_data.oebb_99:
            pass_json["expirationDate"] = ticket_data.oebb_99.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")

            if parsed_layout and parsed_layout.travel_class:
                pass_fields["auxiliaryFields"].append({
                    "key": "class-code",
                    "label": "class-code-label",
                    "value": parsed_layout.travel_class,
                })

            if ticket_data.oebb_99.train_number:
                pass_json["relevantDate"] = ticket_data.oebb_99.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                pass_fields["headerFields"].append({
                    "key": "train-number",
                    "label": "train-number-label",
                    "value": str(ticket_data.oebb_99.train_number),
                    "semantics": {
                        "vehicleNumber": str(ticket_data.oebb_99.train_number)
                    }
                })
                if ticket_data.oebb_99.carriage_number:
                    pass_fields["auxiliaryFields"].append({
                        "key": "coach-number",
                        "label": "coach-number-label",
                        "value": str(ticket_data.oebb_99.carriage_number),
                    })
                pass_fields["secondaryFields"].append({
                    "key": "departure-time",
                    "label": "departure-time-label",
                    "dateStyle": "PKDateStyleMedium",
                    "timeStyle": "PKDateStyleMedium",
                    "value": ticket_data.oebb_99.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
                pass_fields["secondaryFields"].append({
                    "key": "arrival-time",
                    "label": "arrival-time-label",
                    "dateStyle": "PKDateStyleMedium",
                    "timeStyle": "PKDateStyleMedium",
                    "value": ticket_data.oebb_99.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
            else:
                pass_fields["secondaryFields"].append({
                    "key": "validity-start",
                    "label": "validity-start-label",
                    "dateStyle": "PKDateStyleMedium",
                    "timeStyle": "PKDateStyleNone",
                    "value": ticket_data.oebb_99.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
                pass_fields["secondaryFields"].append({
                    "key": "validity-end",
                    "label": "validity-end-label",
                    "dateStyle": "PKDateStyleMedium",
                    "timeStyle": "PKDateStyleNone",
                    "value": ticket_data.oebb_99.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "changeMessage": "validity-end-change"
                })

            if parsed_layout and parsed_layout.document_type:
                pass_fields["backFields"].append({
                    "key": "document-type",
                    "label": "product-label",
                    "value": parsed_layout.document_type,
                })

            pass_fields["backFields"].append({
                "key": "validity-start-back",
                "label": "validity-start-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleFull",
                "value": ticket_data.oebb_99.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            pass_fields["backFields"].append({
                "key": "validity-end-back",
                "label": "validity-end-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleFull",
                "value": ticket_data.oebb_99.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })

            if parsed_layout and parsed_layout.traveller:
                pass_fields["backFields"].append({
                    "key": "traveller",
                    "label": "passenger-label",
                    "value": parsed_layout.traveller,
                })

            if parsed_layout and parsed_layout.train_data:
                pass_fields["backFields"].append({
                    "key": "train-data",
                    "label": "train-number-label",
                    "value": parsed_layout.train_data,
                })

            if parsed_layout and parsed_layout.extra:
                pass_fields["backFields"].append({
                    "key": "extra-data",
                    "label": "other-data-label",
                    "value": parsed_layout.extra,
                })

            if parsed_layout and parsed_layout.operator_rics:
                if carrier := uic.rics.get_rics(parsed_layout.operator_rics):
                    if carrier["url"]:
                        pass_fields["backFields"].append({
                            "key": "carrier",
                            "label": "carrier-label",
                            "value": carrier["full_name"],
                            "attributedValue": f"<a href=\"{carrier['url']}\">{carrier['full_name']}</a>",
                        })
                    else:
                        pass_fields["backFields"].append({
                            "key": "carrier",
                            "label": "carrier-label",
                            "value": carrier["full_name"],
                        })
                else:
                    pass_fields["backFields"].append({
                        "key": "carrier",
                        "label": "carrier-label",
                        "value": parsed_layout.operator_rics,
                    })

            if parsed_layout and parsed_layout.price:
                pass_fields["backFields"].append({
                    "key": "price",
                    "label": "price-label",
                    "value": parsed_layout.price,
                })

            if parsed_layout and parsed_layout.conditions:
                pass_fields["backFields"].append({
                    "key": "conditions",
                    "label": "product-conditions-label",
                    "value": parsed_layout.conditions,
                })

            if parsed_layout and parsed_layout.trips:
                pass_type = "boardingPass"
                pass_fields["transitType"] = "PKTransitTypeTrain"

                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": parsed_layout.trips[0].departure_station,
                    "semantics": {
                        "departureStationName": parsed_layout.trips[0].departure_station
                    }
                })
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": parsed_layout.trips[0].arrival_station,
                    "semantics": {
                        "departureStationName": parsed_layout.trips[0].arrival_station,
                    }
                })

        elif ticket_data.dt_ti or ticket_data.dt_pa:
            if ticket_data.dt_ti:
                if ticket_data.dt_ti.product_name:
                    pass_fields["headerFields"].append({
                        "key": "product",
                        "label": "product-label",
                        "value": ticket_data.dt_ti.product_name,
                    })
                    pass_fields["backFields"].append({
                        "key": "product-back",
                        "label": "product-label",
                        "value": ticket_data.dt_ti.product_name,
                    })

                if ticket_data.dt_ti.validity_start:
                    pass_json["relevantDate"] = ticket_data.dt_ti.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                    pass_fields["secondaryFields"].append({
                        "key": "validity-start",
                        "label": "validity-start-label",
                        "dateStyle": "PKDateStyleMedium",
                        "timeStyle": "PKDateStyleNone",
                        "value": ticket_data.dt_ti.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })
                    pass_fields["backFields"].append({
                        "key": "validity-start-back",
                        "label": "validity-start-label",
                        "dateStyle": "PKDateStyleFull",
                        "timeStyle": "PKDateStyleFull",
                        "value": ticket_data.dt_ti.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })

                if ticket_data.dt_ti.validity_end:
                    pass_json["expirationDate"] = ticket_data.dt_ti.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                    pass_fields["secondaryFields"].append({
                        "key": "validity-end",
                        "label": "validity-end-label",
                        "dateStyle": "PKDateStyleMedium",
                        "timeStyle": "PKDateStyleNone",
                        "value": ticket_data.dt_ti.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "changeMessage": "validity-end-change"
                    })
                    pass_fields["backFields"].append({
                        "key": "validity-end-back",
                        "label": "validity-end-label",
                        "dateStyle": "PKDateStyleFull",
                        "timeStyle": "PKDateStyleFull",
                        "value": ticket_data.dt_ti.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })

            if ticket_data.dt_pa and ticket_data.dt_pa.passenger_name:
                pass_fields["primaryFields"].append({
                    "key": "passenger",
                    "label": "passenger-label",
                    "value": ticket_data.dt_pa.passenger_name,
                })

        elif ticket_data.vor_fi or ticket_data.vor_vd:
            if ticket_data.vor_fi:
                pass_fields["secondaryFields"].append({
                    "key": "validity-start",
                    "label": "validity-start-label",
                    "dateStyle": "PKDateStyleMedium",
                    "timeStyle": "PKDateStyleNone",
                    "value": ticket_data.vor_fi.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
                pass_fields["backFields"].append({
                    "key": "validity-start-back",
                    "label": "validity-start-label",
                    "dateStyle": "PKDateStyleFull",
                    "timeStyle": "PKDateStyleFull",
                    "value": ticket_data.vor_fi.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })

                if ticket_data.vor_fi.validity_end:
                    pass_json["expirationDate"] = ticket_data.vor_fi.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                    pass_fields["secondaryFields"].append({
                        "key": "validity-end",
                        "label": "validity-end-label",
                        "dateStyle": "PKDateStyleMedium",
                        "timeStyle": "PKDateStyleNone",
                        "value": ticket_data.vor_fi.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "changeMessage": "validity-end-change"
                    })
                    pass_fields["backFields"].append({
                        "key": "validity-end-back",
                        "label": "validity-end-label",
                        "dateStyle": "PKDateStyleFull",
                        "timeStyle": "PKDateStyleFull",
                        "value": ticket_data.vor_fi.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })

            if ticket_data.vor_vd:
                if ticket_data.vor_vd.forename and ticket_data.vor_vd.surname:
                    name_value = f"{ticket_data.vor_vd.forename}\n{ticket_data.vor_vd.surname}"
                elif ticket_data.vor_vd.forename:
                    name_value = ticket_data.vor_vd.forename
                elif ticket_data.vor_vd.surname:
                    name_value = ticket_data.vor_vd.surname
                else:
                    name_value = ""
                if name_value:
                    pass_fields["primaryFields"].append({
                        "key": "passenger",
                        "label": "passenger-label",
                        "value": name_value,
                        "semantics": {
                            "passengerName": {
                                "familyName": ticket_data.vor_vd.surname,
                                "givenName": ticket_data.vor_vd.forename
                            }
                        }
                    })
                if ticket_data.vor_vd.date_of_birth:
                    pass_fields["secondaryFields"].append({
                        "key": "date-of-birth",
                        "label": "date-of-birth-label",
                        "dateStyle": "PKDateStyleMedium",
                        "value": ticket_data.vor_vd.date_of_birth.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })

        elif parsed_layout:
            if parsed_layout.trips:
                if parsed_layout.trips[0].departure_station or parsed_layout.trips[0].arrival_station:
                    pass_type = "boardingPass"
                    pass_fields["transitType"] = "PKTransitTypeTrain"

                    pass_fields["primaryFields"].append({
                        "key": "from-station",
                        "label": "from-station-label",
                        "value": parsed_layout.trips[0].departure_station,
                        "semantics": {
                            "departureStationName": parsed_layout.trips[0].departure_station
                        }
                    })
                    pass_fields["primaryFields"].append({
                        "key": "to-station",
                        "label": "to-station-label",
                        "value": parsed_layout.trips[0].arrival_station,
                        "semantics": {
                            "departureStationName": parsed_layout.trips[0].arrival_station,
                        }
                    })

                    if parsed_layout.trips[0].departure:
                        pass_fields["secondaryFields"].append({
                            "key": "departure-time",
                            "label": "departure-time-label",
                            "dateStyle": "PKDateStyleMedium",
                            "timeStyle": "PKDateStyleMedium",
                            "value": parsed_layout.trips[0].departure.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "ignoresTimeZone": True
                        })
                    elif parsed_layout.trips[0].departure_time:
                        pass_fields["secondaryFields"].append({
                            "key": "departure-time",
                            "label": "departure-time-label",
                            "value": f"{parsed_layout.trips[0].departure_date} {parsed_layout.trips[0].departure_time}",
                        })
                    elif parsed_layout.trips[0].departure_date:
                        pass_fields["secondaryFields"].append({
                            "key": "valid-from",
                            "label": "validity-start-label",
                            "value": parsed_layout.trips[0].departure_date
                        })

                    if parsed_layout.trips[0].arrival:
                        pass_fields["secondaryFields"].append({
                            "key": "arrival-time",
                            "label": "arrival-time-label",
                            "dateStyle": "PKDateStyleMedium",
                            "timeStyle": "PKDateStyleMedium",
                            "value": parsed_layout.trips[0].arrival.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "ignoresTimeZone": True
                        })
                    elif parsed_layout.trips[0].arrival_time:
                        pass_fields["secondaryFields"].append({
                            "key": "arrival-time",
                            "label": "arrival-time-label",
                            "value": f"{parsed_layout.trips[0].arrival_date} {parsed_layout.trips[0].arrival_time}",
                        })
                    elif parsed_layout.trips[0].arrival_date:
                        pass_fields["secondaryFields"].append({
                            "key": "valid-until",
                            "label": "validity-end-label",
                            "value": parsed_layout.trips[0].arrival_date
                        })

                else:
                    if parsed_layout.trips[0].departure:
                        pass_fields["secondaryFields"].append({
                            "key": "validity-start",
                            "label": "validity-start-label",
                            "dateStyle": "PKDateStyleMedium",
                            "timeStyle": "PKDateStyleMedium",
                            "value": parsed_layout.trips[0].departure.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "ignoresTimeZone": True
                        })
                    elif parsed_layout.trips[0].departure_time:
                        pass_fields["secondaryFields"].append({
                            "key": "validity-start",
                            "label": "validity-start-label",
                            "value": f"{parsed_layout.trips[0].departure_date} {parsed_layout.trips[0].departure_time}",
                        })
                    elif parsed_layout.trips[0].departure_date:
                        pass_fields["secondaryFields"].append({
                            "key": "validity-start",
                            "label": "validity-start-label",
                            "value": parsed_layout.trips[0].departure_date
                        })

                    if parsed_layout.trips[0].arrival:
                        pass_fields["secondaryFields"].append({
                            "key": "validity-end",
                            "label": "validity-end-label",
                            "dateStyle": "PKDateStyleMedium",
                            "timeStyle": "PKDateStyleMedium",
                            "value": parsed_layout.trips[0].arrival.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "ignoresTimeZone": True
                        })
                    elif parsed_layout.trips[0].arrival_time:
                        pass_fields["secondaryFields"].append({
                            "key": "validity-end",
                            "label": "validity-end-label",
                            "value": f"{parsed_layout.trips[0].arrival_date} {parsed_layout.trips[0].arrival_time}",
                        })
                    elif parsed_layout.trips[0].arrival_date:
                        pass_fields["secondaryFields"].append({
                            "key": "validity-end",
                            "label": "validity-end-label",
                            "value": parsed_layout.trips[0].arrival_date
                        })

            if parsed_layout.travel_class and parsed_layout.travel_class != "0":
                if pass_type == "boardingPass":
                    pass_fields["auxiliaryFields"].append({
                        "key": "class-code",
                        "label": "class-code-label",
                        "value": parsed_layout.travel_class,
                    })
                else:
                    pass_fields["headerFields"].append({
                        "key": "class-code",
                        "label": "class-code-label",
                        "value": parsed_layout.travel_class,
                    })

            if parsed_layout.document_type:
                pass_fields["backFields"].append({
                    "key": "document-type",
                    "label": "product-label",
                    "value": parsed_layout.document_type,
                })

            if parsed_layout.traveller:
                pass_fields["backFields"].append({
                    "key": "traveller",
                    "label": "passenger-label",
                    "value": parsed_layout.traveller,
                })

            if parsed_layout.train_data:
                pass_fields["backFields"].append({
                    "key": "train-data",
                    "label": "train-number-label",
                    "value": parsed_layout.train_data.replace("<", "%lt;"),
                })

            if parsed_layout.extra:
                if pass_fields["secondaryFields"]:
                    pass_fields["backFields"].append({
                        "key": "extra-data",
                        "label": "other-data-label",
                        "value": parsed_layout.extra.replace("<", "%lt;"),
                    })
                else:
                    pass_fields["secondaryFields"].append({
                        "key": "extra-data",
                        "value": parsed_layout.extra.replace("<", "%lt;"),
                    })

            if parsed_layout.operator_rics:
                if carrier := uic.rics.get_rics(parsed_layout.operator_rics):
                    if carrier["url"]:
                        pass_fields["backFields"].append({
                            "key": "carrier",
                            "label": "carrier-label",
                            "value": carrier["full_name"],
                            "attributedValue": f"<a href=\"{carrier['url']}\">{carrier['full_name']}</a>",
                        })
                    else:
                        pass_fields["backFields"].append({
                            "key": "carrier",
                            "label": "carrier-label",
                            "value": carrier["full_name"],
                        })
                else:
                    pass_fields["backFields"].append({
                        "key": "carrier",
                        "label": "carrier-label",
                        "value": parsed_layout.operator_rics,
                    })

            if parsed_layout.price:
                pass_fields["backFields"].append({
                    "key": "price",
                    "label": "price-label",
                    "value": parsed_layout.price,
                })

            if parsed_layout.conditions:
                pass_fields["backFields"].append({
                    "key": "conditions",
                    "label": "product-conditions-label",
                    "value": parsed_layout.conditions.replace("<", "%lt;"),
                })

        if distributor := ticket_data.distributor():
            pass_json["organizationName"] = distributor["full_name"]
            if distributor["url"]:
                pass_fields["backFields"].append({
                    "key": "issuing-org",
                    "label": "issuing-organisation-label",
                    "value": distributor["full_name"],
                    "attributedValue": f"<a href=\"{distributor['url']}\">{distributor['full_name']}</a>",
                })
                return_pass_fields["backFields"].append({
                    "key": "issuing-org",
                    "label": "issuing-organisation-label",
                    "value": distributor["full_name"],
                    "attributedValue": f"<a href=\"{distributor['url']}\">{distributor['full_name']}</a>",
                })
            else:
                pass_fields["backFields"].append({
                    "key": "distributor",
                    "label": "issuing-organisation-label",
                    "value": distributor["full_name"],
                })
                return_pass_fields["backFields"].append({
                    "key": "distributor",
                    "label": "issuing-organisation-label",
                    "value": distributor["full_name"],
                })

        pass_fields["backFields"].append({
            "key": "issued-date",
            "label": "issued-at-label",
            "dateStyle": "PKDateStyleFull",
            "timeStyle": "PKDateStyleFull",
            "value": issued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        return_pass_fields["backFields"].append({
            "key": "issued-date",
            "label": "issued-at-label",
            "dateStyle": "PKDateStyleFull",
            "timeStyle": "PKDateStyleFull",
            "value": issued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    elif isinstance(ticket_instance, models.VDVTicketInstance):
        ticket_data: ticket.VDVTicket = ticket_instance.as_ticket()

        validity_start = ticket_data.ticket.validity_start.as_datetime().astimezone(pytz.utc)
        validity_end = ticket_data.ticket.validity_end.as_datetime().astimezone(pytz.utc)
        issued_at = ticket_data.ticket.transaction_time.as_datetime().astimezone(pytz.utc)

        pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        pass_fields = {
            "headerFields": [{
                "key": "product",
                "label": "product-label",
                "value": ticket_data.ticket.product_name()
            }],
            "primaryFields": [],
            "secondaryFields": [{
                "key": "validity-start",
                "label": "validity-start-label",
                "dateStyle": "PKDateStyleMedium",
                "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, {
                "key": "validity-end",
                "label": "validity-end-label",
                "dateStyle": "PKDateStyleMedium",
                "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "changeMessage": "validity-end-change"
            }],
            "backFields": [{
                "key": "validity-start-back",
                "label": "validity-start-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleFull",
                "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, {
                "key": "validity-end-back",
                "label": "validity-end-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleFull",
                "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, {
                "key": "product-back",
                "label": "product-label",
                "value": ticket_data.ticket.product_name()
            }, {
                "key": "product-org-back",
                "label": "product-organisation-label",
                "value": ticket_data.ticket.product_org_name()
            }, {
                "key": "ticket-id",
                "label": "ticket-id-label",
                "value": str(ticket_data.ticket.ticket_id),
            }, {
                "key": "ticket-org",
                "label": "ticketing-organisation-label",
                "value": ticket_data.ticket.ticket_org_name(),
            }, {
                "key": "issued-date",
                "label": "issued-at-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleFull",
                "value": issued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, {
                "key": "issuing-org",
                "label": "issuing-organisation-label",
                "value": ticket_data.ticket.kvp_org_name(),
            }]
        }
        pass_json["organizationName"] = ticket_data.ticket.kvp_org_name()
        pass_json["barcodes"] = [{
            "format": "PKBarcodeFormatAztec",
            "message": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
            "messageEncoding": "iso-8859-1",
            "altText": str(ticket_data.ticket.ticket_id),
        }]

        for elm in ticket_data.ticket.product_data:
            if isinstance(elm, vdv.ticket.PassengerData):
                if elm.forename and elm.surname:
                    name_value = f"{elm.forename}\n{elm.surname}"
                elif elm.forename:
                    name_value = elm.forename
                elif elm.surname:
                    name_value = elm.surname
                else:
                    name_value = ""
                if name_value:
                    pass_fields["primaryFields"].append({
                        "key": "passenger",
                        "label": "passenger-label",
                        "value": name_value,
                        "semantics": {
                            "passengerName": {
                                "familyName": elm.surname,
                                "givenName": elm.forename
                            }
                        }
                    })
                if elm.date_of_birth:
                    pass_fields["secondaryFields"].append({
                        "key": "date-of-birth",
                        "label": "date-of-birth-label",
                        "dateStyle": "PKDateStyleMedium",
                        "value": elm.date_of_birth.as_date().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })
            elif isinstance(elm, vdv.ticket.SpacialValidity):
                if elm.organization_id == 6100:  # Verhkersverbund Berlin Brandenburg
                    if elm.area == 1200:
                        add_pkp_img(pkp, "pass/berlin-ab.png", "thumbnail.png")
                    elif elm.area == 1202:
                        add_pkp_img(pkp, "pass/berlin-abc.png", "thumbnail.png")

        org_id = ticket_data.ticket.product_org_id if ticket_data.ticket.product_org_id not in (3000, 5000)\
            else ticket_data.ticket.ticket_org_id
        if org_id in VDV_ORG_ID_LOGO:
            add_pkp_img(pkp, VDV_ORG_ID_LOGO[org_id], "logo.png")
            have_logo = True
        if org_id in VDV_ORG_ID_BG:
            pass_json["backgroundColor"] = VDV_ORG_ID_BG[org_id]
        if org_id in VDV_ORG_ID_FG:
            pass_json["foregroundColor"] = VDV_ORG_ID_FG[org_id]
        if org_id in VDV_ORG_ID_FG_SECONDARY:
            pass_json["labelColor"] = VDV_ORG_ID_FG_SECONDARY[org_id]

    elif isinstance(ticket_instance, models.RSPTicketInstance):
        ticket_data: ticket.RSPTicket = ticket_instance.as_ticket()

        pass_json["barcodes"] = [{
            "format": "PKBarcodeFormatAztec",
            "message": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
            "messageEncoding": "iso-8859-1",
            "altText": f"{ticket_instance.issuer_id}-{ticket_instance.reference}",
        }]
        pass_json["organizationName"] = ticket_data.issuer_name()

        if isinstance(ticket_data.data, rsp.TicketData):
            validity_start = ticket_data.data.validity_start_time()
            validity_end = ticket_data.data.validity_end_time()

            pass_json["relevantDate"] = validity_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
            pass_type = "boardingPass"
            pass_fields = {
                "transitType": "PKTransitTypeTrain",
                "headerFields": [{
                    "key": "departure-time",
                    "label": "departure-time-label",
                    "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "dateStyle": "PKDateStyleShort",
                    "timeStyle": "PKDateStyleShort" if ticket_data.data.depart_time_flag == 2 else "PKDateStyleNone",
                }],
                "primaryFields": [],
                "auxiliaryFields": [{
                    "key": "travel-class",
                    "label": "class-code-label",
                    "value": "class-code-second-label" if ticket_data.data.standard_class else "class-code-first-label",
                }],
                "secondaryFields": [],
                "backFields": [],
            }

            if from_station := rsp.ticket_data.get_station_by_nlc(ticket_data.data.origin_nlc):
                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": from_station.crs_code,
                    "semantics": {
                        "departureLocation": {
                            "latitude": float(from_station.latitude),
                            "longitude": float(from_station.longitude),
                        },
                        "departureStationName": from_station.name,
                    }
                })
                maps_link = urllib.parse.urlencode({
                    "q": from_station.name,
                    "ll": f"{from_station.latitude},{from_station.longitude}"
                })
                pass_fields["backFields"].append({
                    "key": "from-station-back",
                    "label": "from-station-label",
                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{from_station.name}</a>",
                })
            elif from_station := rsp.locations.get_station_by_nlc(ticket_data.data.origin_nlc):
                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": from_station["3ALPHA"],
                    "semantics": {
                        "departureStationName": from_station["NLCDESC"]
                    }
                })
                pass_fields["backFields"].append({
                    "key": "from-station-back",
                    "label": "from-station-label",
                    "value": from_station["NLCDESC"]
                })

            if to_station := rsp.ticket_data.get_station_by_nlc(ticket_data.data.destination_nlc):
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": to_station.crs_code,
                    "semantics": {
                        "departureLocation": {
                            "latitude": float(to_station.latitude),
                            "longitude": float(to_station.longitude),
                        },
                        "departureStationName": to_station.name,
                    }
                })
                maps_link = urllib.parse.urlencode({
                    "q": to_station.name,
                    "ll": f"{to_station.latitude},{to_station.longitude}"
                })
                pass_fields["backFields"].append({
                    "key": "to-station-back",
                    "label": "to-station-label",
                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{to_station.name}</a>",
                })
            elif to_station := rsp.locations.get_station_by_nlc(ticket_data.data.destination_nlc):
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": to_station["3ALPHA"],
                    "semantics": {
                        "departureStationName": to_station["NLCDESC"]
                    }
                })
                pass_fields["backFields"].append({
                    "key": "to-station-back",
                    "label": "to-station-label",
                    "value": to_station["NLCDESC"]
                })

            pass_fields["backFields"].append({
                "key": "return-included",
                "label": "return-included-label",
                "value": "return-included-yes" if ticket_data.data.bidirectional else "return-included-no",
            })
            pass_fields["backFields"].append({
                "key": "issuing-org",
                "label": "issuing-organisation-label",
                "value": ticket_data.issuer_name(),
            })

            if ticket_data.data.passenger_name:
                pass_fields["secondaryFields"].append({
                    "key": "passenger-name",
                    "label": "passenger-label",
                    "value": ticket_data.data.passenger_name,
                })

            if ticket_data.data.purchase_data:
                pass_fields["backFields"].extend([{
                    "key": "ticket-id",
                    "label": "ticket-id-label",
                    "value": ticket_data.data.purchase_data.purchase_reference or ticket_data.ticket_ref,
                }, {
                    "key": "issued-date",
                    "label": "issued-at-label",
                    "dateStyle": "PKDateStyleFull",
                    "timeStyle": "PKDateStyleFull",
                    "value": ticket_data.data.purchase_data.purchase_time().strftime("%Y-%m-%dT%H:%M:%SZ"),
                }, {
                    "key": "price",
                    "label": "price-label",
                    "value": ticket_data.data.purchase_data.price_str()
                }])

            if discount_data := rsp.ticket_data.get_discount_by_id(ticket_data.data.discount_code):
                if discount_data["description"]:
                    pass_fields["secondaryFields"].append({
                        "key": "discount",
                        "label": "reduction-card-label",
                        "value": discount_data["description"]
                    })

            for i, reservation in enumerate(ticket_data.data.reservations):
                pass_fields["secondaryFields"].append({
                    "key": f"reservation-{i}-service",
                    "label": "train-number-label",
                    "value": reservation.service_id,
                })
                if reservation.coach:
                    pass_fields["auxiliaryFields"].append({
                        "key": f"reservation-{i}-coach",
                        "label": "coach-number-label",
                        "value": reservation.coach,
                    })
                if reservation.seat:
                    pass_fields["auxiliaryFields"].append({
                        "key": f"reservation-{i}-seat",
                        "label": "seat-number-label",
                        "value": reservation.seat,
                    })

            if route_data := rsp.ticket_data.get_route_by_id(ticket_data.data.route_code):
                pass_fields["auxiliaryFields"].append({
                    "key": "route",
                    "label": "route-label",
                    "value": route_data["cc_desc"]
                })
                pass_fields["backFields"].append({
                    "key": "route-description",
                    "label": "route-label",
                    "value": route_data["atb_desc"]
                })
                if route_data["all_included_crs"]:
                    stations = []
                    for crs in route_data["all_included_crs"]:
                        if station := rsp.ticket_data.get_station_by_crs(crs):
                            if station.latitude and station.longitude:
                                maps_link = urllib.parse.urlencode({
                                    "q": station.name,
                                    "ll": f"{station.latitude},{station.longitude}"
                                })
                                stations.append(f"<a href=\"https://maps.apple.com/?{maps_link}\">{station.name}</a>")
                            else:
                                stations.append(station.name)
                        else:
                            stations.append(crs)
                    pass_fields["backFields"].append({
                        "key": "all-included-crs",
                        "label": "travel-via-all-label",
                        "value": "\n".join(stations)
                    })
                if route_data["any_included_crs"]:
                    stations = []
                    for crs in route_data["any_included_crs"]:
                        if station := rsp.ticket_data.get_station_by_crs(crs):
                            if station.latitude and station.longitude:
                                maps_link = urllib.parse.urlencode({
                                    "q": station.name,
                                    "ll": f"{station.latitude},{station.longitude}"
                                })
                                stations.append(f"<a href=\"https://maps.apple.com/?{maps_link}\">{station.name}</a>")
                            else:
                                stations.append(station.name)
                        else:
                            stations.append(crs)
                    pass_fields["backFields"].append({
                        "key": "any-included-crs",
                        "label": "travel-via-any-label",
                        "value": "\n".join(stations)
                    })
                if route_data["excluded_crs"]:
                    stations = []
                    for crs in route_data["excluded_crs"]:
                        if station := rsp.ticket_data.get_station_by_crs(crs):
                            if station.latitude and station.longitude:
                                maps_link = urllib.parse.urlencode({
                                    "q": station.name,
                                    "ll": f"{station.latitude},{station.longitude}"
                                })
                                stations.append(f"<a href=\"https://maps.apple.com/?{maps_link}\">{station.name}</a>")
                            else:
                                stations.append(station.name)
                        else:
                            stations.append(crs)
                    pass_fields["backFields"].append({
                        "key": "excluded-crs",
                        "label": "travel-via-excl-label",
                        "value": "\n".join(stations)
                    })
                if route_data["included_tocs"]:
                    tocs = []
                    for toc in route_data["included_tocs"]:
                        if toc_data := rsp.ticket_data.get_toc_by_id(toc):
                            tocs.append(toc_data["name"])
                        else:
                            tocs.append(toc)
                    pass_fields["backFields"].append({
                        "key": "included-toc",
                        "label": "travel-inc-toc-label",
                        "value": "\n".join(tocs)
                    })
                if route_data["excluded_tocs"]:
                    tocs = []
                    for toc in route_data["excluded_tocs"]:
                        if toc_data := rsp.ticket_data.get_toc_by_id(toc):
                            tocs.append(toc_data["name"])
                        else:
                            tocs.append(toc)
                    pass_fields["backFields"].append({
                        "key": "excluded-toc",
                        "label": "travel-excl-toc-label",
                        "value": "\n".join(tocs)
                    })

            if ticket_type := rsp.ticket_data.get_ticket_type(ticket_data.data.fare_label):
                def format_text(text):
                    return text.replace("</p>", "\n\n").replace('title=""', "").strip()

                pass_fields["secondaryFields"].append({
                    "key": "product",
                    "label": "product-label",
                    "value": ticket_type.ticket_type_name,
                })
                if ticket_type.validity:
                    if ticket_type.validity.day_outward:
                        pass_fields["backFields"].append({
                            "key": "product-validity-outward-date",
                            "label": "product-validity-outward-date-label",
                            "attributedValue": format_text(ticket_type.validity.day_outward),
                        })
                    if ticket_type.validity.time_outward:
                        pass_fields["backFields"].append({
                            "key": "product-validity-outward-time",
                            "label": "product-validity-outward-time-label",
                            "attributedValue": format_text(ticket_type.validity.time_outward),
                        })
                    if ticket_type.validity.day_return:
                        pass_fields["backFields"].append({
                            "key": "product-validity-return-date",
                            "label": "product-validity-return-date-label",
                            "attributedValue": format_text(ticket_type.validity.day_return),
                        })
                    if ticket_type.validity.time_return:
                        pass_fields["backFields"].append({
                            "key": "product-validity-return-time",
                            "label": "product-validity-return-time-label",
                            "attributedValue": format_text(ticket_type.validity.time_return),
                        })
                if ticket_type.break_of_journey:
                    if ticket_type.break_of_journey.outward_note:
                        pass_fields["backFields"].append({
                            "key": "product-break-of-journey-outward",
                            "label": "product-break-of-journey-outward-label",
                            "attributedValue": format_text(ticket_type.break_of_journey.outward_note),
                        })
                    if ticket_type.break_of_journey.return_note:
                        pass_fields["backFields"].append({
                            "key": "product-break-of-journey-return",
                            "label": "product-break-of-journey-return-label",
                            "attributedValue": format_text(ticket_type.break_of_journey.return_note),
                        })
                if ticket_type.conditions:
                    pass_fields["backFields"].append({
                        "key": "product-conditions",
                        "label": "product-conditions-label",
                        "attributedValue": format_text(ticket_type.conditions),
                    })
                if ticket_type.changes_to_travel_plans:
                    pass_fields["backFields"].append({
                        "key": "product-changes",
                        "label": "product-changes-label",
                        "attributedValue": format_text(ticket_type.changes_to_travel_plans),
                    })
                if ticket_type.refunds:
                    pass_fields["backFields"].append({
                        "key": "product-refunds",
                        "label": "product-refunds-label",
                        "attributedValue": format_text(ticket_type.refunds),
                    })

            if ticket_data.issuer_id in RSP_ORG_LOGO:
                add_pkp_img(pkp, RSP_ORG_LOGO[ticket_data.issuer_id], "logo.png")
                have_logo = True
            else:
                add_pkp_img(pkp, "pass/logo-nr.png", "logo.png")
                have_logo = True

        elif isinstance(ticket_data.data, rsp.RailcardData):
            validity_start = ticket_data.data.validity_start_time()
            validity_end = ticket_data.data.validity_end_time()
            pass_json["organizationName"] = ticket_data.data.issuer_name()
            if colour := ticket_data.data.background_colour():
                pass_json["backgroundColor"] = colour
                pass_json["foregroundColor"] = "rgb(255, 255, 255)"
                pass_json["labelColor"] = "rgb(205, 205, 205)"

            pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
            pass_fields = {
                "headerFields": [{
                    "key": "product",
                    "label": "product-label",
                    "value": ticket_data.data.railcard_type_name(),
                }],
                "primaryFields": [{
                    "key": "passenger",
                    "label": "passenger-label",
                    "value": f"{ticket_data.data.passenger_1_forename}\n{ticket_data.data.passenger_1_surname}",
                    "semantics": {
                        "passengerName": {
                            "familyName": ticket_data.data.passenger_1_surname,
                            "givenName": ticket_data.data.passenger_1_forename,
                        }
                    }
                }],
                "secondaryFields": [{
                    "key": "railcard-number",
                    "label": "railcard-number",
                    "value": ticket_data.data.railcard_number,
                }, {
                    "key": "validity-end",
                    "label": "validity-end-label",
                    "dateStyle": "PKDateStyleMedium",
                    "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "changeMessage": "validity-end-change"
                }],
                "backFields": [{
                    "key": "validity-start-back",
                    "label": "validity-start-label",
                    "dateStyle": "PKDateStyleFull",
                    "timeStyle": "PKDateStyleFull",
                    "value": validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }, {
                    "key": "validity-end-back",
                    "label": "validity-end-label",
                    "dateStyle": "PKDateStyleFull",
                    "timeStyle": "PKDateStyleFull",
                    "value": validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }, {
                    "key": "issuing-org",
                    "label": "issuing-organisation-label",
                    "value": ticket_data.data.issuer_name(),
                }, {
                    "key": "ticket-id",
                    "label": "ticket-id-label",
                    "value": str(ticket_data.data.ticket_reference),
                }, {
                    "key": "issued-date",
                    "label": "issued-at-label",
                    "dateStyle": "PKDateStyleFull",
                    "timeStyle": "PKDateStyleFull",
                    "value": ticket_data.data.purchase_time().strftime("%Y-%m-%dT%H:%M:%SZ"),
                }]
            }

            if ticket_data.data.has_passenger_2():
                pass_fields["primaryFields"].append({
                    "key": "passenger-2",
                    "label": "passenger-2-label",
                    "value": ticket_data.data.passenger_2_name(),
                    "semantics": {
                        "passengerName": {
                            "familyName": ticket_data.data.passenger_2_surname,
                            "givenName": ticket_data.data.passenger_2_forename,
                        }
                    }
                })

            thumb = pass_photo_thumbnail(ticket_obj, (270, 270), 20)
            out_3x = io.BytesIO()
            thumb.save(out_3x, format="PNG")
            out_2x = io.BytesIO()
            thumb.resize((180, 180)).save(out_2x, format="PNG")
            out_1x = io.BytesIO()
            thumb.resize((90, 90)).save(out_1x, format="PNG")
            pkp.add_file(f"thumbnail@3x.png", out_3x.getvalue())
            pkp.add_file(f"thumbnail@2x.png", out_2x.getvalue())
            pkp.add_file(f"thumbnail.png", out_1x.getvalue())

            add_pkp_img(pkp, "pass/logo-nr.png", "logo.png")
            have_logo = True
    elif isinstance(ticket_instance, models.SNCFTicketInstance):
        ticket_data: ticket.SNCFTicket = ticket_instance.as_ticket()

        pass_type = "boardingPass"

        from_station = templatetags.rics.get_station(ticket_data.data.departure_station, "sncf")
        to_station = templatetags.rics.get_station(ticket_data.data.arrival_station, "sncf")

        tz = pytz.timezone('Europe/Paris')
        now = timezone.now()
        travel_date = ticket_data.data.travel_date.replace(year=now.year)
        if travel_date < now.date():
            travel_date = travel_date.replace(year=travel_date.year + 1)
        travel_datetime = tz.localize(datetime.datetime.combine(travel_date, datetime.time.min))\
            .astimezone(pytz.utc)
        pass_json["relevantDate"] = travel_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

        pass_json["locations"].append({
            "latitude": float(from_station["latitude"]),
            "longitude": float(from_station["longitude"]),
            "relevantText": from_station["name"]
        })
        pass_json["locations"].append({
            "latitude": float(to_station["latitude"]),
            "longitude": float(to_station["longitude"]),
            "relevantText": to_station["name"]
        })
        from_station_maps_link = urllib.parse.urlencode({
            "q": from_station["name"],
            "ll": f"{from_station['latitude']},{from_station['longitude']}"
        })
        to_station_maps_link = urllib.parse.urlencode({
            "q": to_station["name"],
            "ll": f"{to_station['latitude']},{to_station['longitude']}"
        })

        pass_fields = {
            "transitType": "PKTransitTypeTrain",
            "headerFields": [{
                "key": "class-code",
                "label": "class-code-label",
                "value": f"class-code-{ticket_data.data.travel_class}-label",
            }],
            "primaryFields": [{
                "key": "from-station",
                "label": "from-station-label",
                "value": from_station["name"],
                "semantics": {
                    "departureLocation": {
                        "latitude": float(from_station["latitude"]),
                        "longitude": float(from_station["longitude"]),
                    },
                    "departureStationName": from_station["name"]
                }
            }, {
                "key": "to-station",
                "label": "to-station-label",
                "value": to_station["name"],
                "semantics": {
                    "destinationLocation": {
                        "latitude": float(to_station["latitude"]),
                        "longitude": float(to_station["longitude"]),
                    },
                    "destinationStationName": to_station["name"]
                }
            }],
            "auxiliaryFields": [{
                "key": "passenger",
                "label": "passenger-label",
                "value": f"{ticket_data.data.traveler_forename} {ticket_data.data.traveler_surname}",
                "semantics": {
                    "passengerName": {
                        "familyName": ticket_data.data.traveler_surname,
                        "givenName": ticket_data.data.traveler_forename,
                    }
                }
            }, {
                "key": "date-of-birth",
                "label": "date-of-birth-label",
                "dateStyle": "PKDateStyleMedium",
                "value": ticket_data.data.traveler_dob.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }],
            "secondaryFields": [],
            "backFields": [{
                "key": "from-station-back",
                "label": "from-station-label",
                "value": from_station["name"],
                "attributedValue": f"<a href=\"https://maps.apple.com/?{from_station_maps_link}\">{from_station['name']}</a>",
            }, {
                "key": "to-station-back",
                "label": "to-station-label",
                "value": to_station["name"],
                "attributedValue": f"<a href=\"https://maps.apple.com/?{to_station_maps_link}\">{to_station['name']}</a>",
            }, {
                "key": "ticket-id",
                "label": "ticket-id-label",
                "value": str(ticket_data.data.ticket_number),
            }]
        }
        pass_json["organizationName"] = "SNCF"
        pass_json["barcodes"] = [{
            "format": "PKBarcodeFormatAztec",
            "message": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
            "messageEncoding": "iso-8859-1",
            "altText": str(ticket_data.data.pnr)
        }]
        add_pkp_img(pkp, "pass/logo-sncf.png", "logo.png")
        have_logo = True
    elif isinstance(ticket_instance, models.ELBTicketInstance):
        ticket_data: ticket.ELBTicket = ticket_instance.as_ticket()
        validity_end = ticket_data.data.validity_end_time()
        departure_date = ticket_data.data.departure_time()
        pass_type = "boardingPass"
        from_station = templatetags.rics.get_station(ticket_data.data.departure_station, "sncf")
        if not from_station:
            from_station = templatetags.rics.get_station(ticket_data.data.departure_station, "benerail")
        to_station = templatetags.rics.get_station(ticket_data.data.arrival_station, "sncf")
        if not to_station:
            to_station = templatetags.rics.get_station(ticket_data.data.arrival_station, "benerail")

        pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        pass_json["relevantDate"] = departure_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        pass_fields = {
            "transitType": "PKTransitTypeTrain",
            "headerFields": [{
                "key": "departure-date",
                "label": "departure-date-label",
                "value": departure_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "dateStyle": "PKDateStyleMedium",
            }],
            "primaryFields": [],
            "secondaryFields": [{
                "key": "class-code",
                "label": "class-code-label",
                "value": f"class-code-{ticket_data.data.travel_class}-label",
            }],
            "auxiliaryFields": [{
                "key": "train-number",
                "label": "train-number-label",
                "value": ticket_data.data.train_number,
            }, {
                "key": "coach-number",
                "label": "coach-number-label",
                "value": ticket_data.data.coach_number,
            }, {
                "key": "seat-number",
                "label": "seat-number-label",
                "value": ticket_data.data.seat_number,
            }],
            "backFields": []
        }


        if from_station:
            from_station_maps_link = urllib.parse.urlencode({
                "q": from_station["name"],
                "ll": f"{from_station['latitude']},{from_station['longitude']}"
            })
            pass_fields["primaryFields"].append({
                "key": "from-station",
                "label": "from-station-label",
                "value": from_station["name"],
                "semantics": {
                    "departureLocation": {
                        "latitude": float(from_station["latitude"]),
                        "longitude": float(from_station["longitude"]),
                    },
                    "departureStationName": from_station["name"]
                }
            })
            pass_fields["backFields"].append({
                "key": "from-station-back",
                "label": "from-station-label",
                "value": from_station["name"],
                "attributedValue": f"<a href=\"https://maps.apple.com/?{from_station_maps_link}\">{from_station['name']}</a>",
            })
        else:
            pass_fields["primaryFields"].append({
                "key": "from-station",
                "label": "from-station-label",
                "value": ticket_data.data.departure_station,
            })

        if to_station:
            to_station_maps_link = urllib.parse.urlencode({
                "q": to_station["name"],
                "ll": f"{to_station['latitude']},{to_station['longitude']}"
            })
            pass_fields["primaryFields"].append({
                "key": "to-station",
                "label": "to-station-label",
                "value": to_station["name"],
                "semantics": {
                    "destinationLocation": {
                        "latitude": float(to_station["latitude"]),
                        "longitude": float(to_station["longitude"]),
                    },
                    "destinationStationName": to_station["name"]
                }
            })
            pass_fields["backFields"].append({
                "key": "to-station-back",
                "label": "to-station-label",
                "value": to_station["name"],
                "attributedValue": f"<a href=\"https://maps.apple.com/?{to_station_maps_link}\">{to_station['name']}</a>",
            })
        else:
            pass_fields["primaryFields"].append({
                "key": "to-station",
                "label": "to-station-label",
                "value": ticket_data.data.arrival_station,
            })

        pass_fields["backFields"].append({
            "key": "ticket-id",
            "label": "ticket-id-label",
            "value": str(ticket_data.data.booking_number),
        })

        pass_json["barcodes"] = [{
            "format": "PKBarcodeFormatAztec",
            "message": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
            "messageEncoding": "iso-8859-1",
            "altText": f"{ticket_data.data.pnr} {ticket_data.data.sequence_number}"
        }]
        add_pkp_img(pkp, "pass/logo-eurostar.png", "logo.png")
        have_logo = True
    elif isinstance(ticket_instance, models.SSBTicketInstance):
        ticket_data: ticket.SSBTicket = ticket_instance.as_ticket()

        pass_json["barcodes"] = [{
            "format": "PKBarcodeFormatAztec",
            "message": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
            "messageEncoding": "iso-8859-1",
            "altText": ticket_data.data.pnr
        }]

        if isinstance(ticket_data.data, ssb.IntegratedReservationTicket):
            pass_type = "boardingPass"
            pass_fields["transitType"] = "PKTransitTypeTrain"

            pass_fields["backFields"].append({
                "key": "ticket-id",
                "label": "ticket-id-label",
                "value": ticket_data.data.pnr,
                "semantics": {
                    "confirmationNumber": ticket_data.data.pnr,
                }
            })

            if ticket_data.data.departure_station_uic:
                from_station = templatetags.rics.get_station(ticket_data.data.departure_station_uic, "uic")
            elif ticket_data.data.departure_station_benerail:
                from_station = templatetags.rics.get_station(ticket_data.data.departure_station_benerail, "benerail")
            else:
                from_station = None

            if from_station:
                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": from_station["name"],
                    "semantics": {
                        "departureLocation": {
                            "latitude": float(from_station["latitude"]),
                            "longitude": float(from_station["longitude"]),
                        },
                        "departureStationName": from_station["name"]
                    }
                })
                maps_link = urllib.parse.urlencode({
                    "q": from_station["name"],
                    "ll": f"{from_station['latitude']},{from_station['longitude']}"
                })
                pass_fields["backFields"].append({
                    "key": "from-station-back",
                    "label": "from-station-label",
                    "value": from_station["name"],
                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{from_station['name']}</a>",
                })
            elif ticket_data.data.departure_station_name:
                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": ticket_data.data.departure_station_name,
                    "semantics": {
                        "departureStationName": ticket_data.data.departure_station_name,
                    }
                })

            if ticket_data.data.arrival_station_uic:
                to_station = templatetags.rics.get_station(ticket_data.data.arrival_station_uic, "uic")
            elif ticket_data.data.arrival_station_benerail:
                to_station = templatetags.rics.get_station(ticket_data.data.arrival_station_benerail, "benerail")
            else:
                to_station = None

            if to_station:
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": to_station["name"],
                    "semantics": {
                        "departureLocation": {
                            "latitude": float(to_station["latitude"]),
                            "longitude": float(to_station["longitude"]),
                        },
                        "departureStationName": to_station["name"]
                    }
                })
                maps_link = urllib.parse.urlencode({
                    "q": to_station["name"],
                    "ll": f"{to_station['latitude']},{to_station['longitude']}"
                })
                pass_fields["backFields"].append({
                    "key": "to-station-back",
                    "label": "to-station-label",
                    "value": to_station["name"],
                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{to_station['name']}</a>",
                })
            elif ticket_data.data.arrival_station_name:
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": ticket_data.data.arrival_station_name,
                    "semantics": {
                        "departureStationName": ticket_data.data.arrival_station_name,
                    }
                })

            if ticket_data.data.travel_class:
                pass_fields["auxiliaryFields"].append({
                    "key": "class-code",
                    "label": "class-code-label",
                    "value": f"class-code-{ticket_data.data.travel_class}-label",
                })

            if ticket_data.data.train_number:
                pass_fields["headerFields"].append({
                    "key": "train-number",
                    "label": "train-number-label",
                    "value": ticket_data.data.train_number,
                    "semantics": {
                        "vehicleNumber": ticket_data.data.train_number,
                    }
                })

            if ticket_data.data.coach_number:
                pass_fields["auxiliaryFields"].append({
                    "key": "coach-number",
                    "label": "coach-number-label",
                    "value": ticket_data.data.coach_number,
                })

            if ticket_data.data.seat_number:
                pass_fields["auxiliaryFields"].append({
                    "key": "seat-number",
                    "label": "seat-number-label",
                    "value": ticket_data.data.seat_number,
                })

            pass_fields["secondaryFields"].append({
                "key": "departure-time",
                "label": "departure-time-label",
                "dateStyle": "PKDateStyleMedium",
                "timeStyle": "PKDateStyleMedium",
                "value": f"{ticket_data.data.departure.isoformat()}Z",
                "ignoresTimeZone": True
            })
            pass_fields["backFields"].append({
                "key": "issued-date",
                "label": "issued-at-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.issuing_date.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })

            if ticket_data.data.extra_text:
                pass_fields["backFields"].append({
                    "key": "extra-date",
                    "label": "other-data-label",
                    "value": ticket_data.data.extra_text,
                })

        elif isinstance(ticket_data.data, ssb.NonReservationTicket):
            pass_type = "boardingPass"
            pass_fields["transitType"] = "PKTransitTypeTrain"

            pass_fields["backFields"].append({
                "key": "ticket-id",
                "label": "ticket-id-label",
                "value": ticket_data.data.pnr,
                "semantics": {
                    "confirmationNumber": ticket_data.data.pnr,
                }
            })

            if ticket_data.data.departure_station_uic:
                from_station = templatetags.rics.get_station(ticket_data.data.departure_station_uic, "uic")
                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": from_station["name"],
                    "semantics": {
                        "departureLocation": {
                            "latitude": float(from_station["latitude"]),
                            "longitude": float(from_station["longitude"]),
                        },
                        "departureStationName": from_station["name"]
                    }
                })
                maps_link = urllib.parse.urlencode({
                    "q": from_station["name"],
                    "ll": f"{from_station['latitude']},{from_station['longitude']}"
                })
                pass_fields["backFields"].append({
                    "key": "from-station-back",
                    "label": "from-station-label",
                    "value": from_station["name"],
                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{from_station['name']}</a>",
                })
            elif ticket_data.data.departure_station_name:
                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": ticket_data.data.departure_station_name,
                    "semantics": {
                        "departureStationName": ticket_data.data.departure_station_name,
                    }
                })

            if ticket_data.data.arrival_station_uic:
                to_station = templatetags.rics.get_station(ticket_data.data.arrival_station_uic, "uic")
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": to_station["name"],
                    "semantics": {
                        "departureLocation": {
                            "latitude": float(to_station["latitude"]),
                            "longitude": float(to_station["longitude"]),
                        },
                        "departureStationName": to_station["name"]
                    }
                })
                maps_link = urllib.parse.urlencode({
                    "q": to_station["name"],
                    "ll": f"{to_station['latitude']},{to_station['longitude']}"
                })
                pass_fields["backFields"].append({
                    "key": "to-station-back",
                    "label": "to-station-label",
                    "value": to_station["name"],
                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{to_station['name']}</a>",
                })
            elif ticket_data.data.arrival_station_name:
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": ticket_data.data.arrival_station_name,
                    "semantics": {
                        "departureStationName": ticket_data.data.arrival_station_name,
                    }
                })

            if ticket_data.data.travel_class:
                pass_fields["auxiliaryFields"].append({
                    "key": "class-code",
                    "label": "class-code-label",
                    "value": f"class-code-{ticket_data.data.travel_class}-label",
                })

            pass_fields["secondaryFields"].append({
                "key": "validity-start",
                "label": "validity-start-label",
                "dateStyle": "PKDateStyleMedium",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.validity_start.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })
            pass_fields["secondaryFields"].append({
                "key": "validity-end",
                "label": "validity-end-label",
                "dateStyle": "PKDateStyleMedium",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.validity_end.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })
            pass_fields["backFields"].append({
                "key": "issued-date",
                "label": "issued-at-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.issuing_date.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })

            if ticket_data.data.extra_text:
                pass_fields["backFields"].append({
                    "key": "extra-date",
                    "label": "other-data-label",
                    "value": ticket_data.data.extra_text,
                })


        elif isinstance(ticket_data.data, ssb.GroupTicket):
            pass_type = "boardingPass"
            pass_fields["transitType"] = "PKTransitTypeTrain"

            pass_fields["backFields"].append({
                "key": "ticket-id",
                "label": "ticket-id-label",
                "value": ticket_data.data.pnr,
                "semantics": {
                    "confirmationNumber": ticket_data.data.pnr,
                }
            })

            pass_fields["headerFields"].append({
                "key": "group-ticket",
                "value": "group-ticket-label"
            })

            if ticket_data.data.departure_station_uic:
                from_station = templatetags.rics.get_station(ticket_data.data.departure_station_uic, "uic")
                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": from_station["name"],
                    "semantics": {
                        "departureLocation": {
                            "latitude": float(from_station["latitude"]),
                            "longitude": float(from_station["longitude"]),
                        },
                        "departureStationName": from_station["name"]
                    }
                })
                maps_link = urllib.parse.urlencode({
                    "q": from_station["name"],
                    "ll": f"{from_station['latitude']},{from_station['longitude']}"
                })
                pass_fields["backFields"].append({
                    "key": "from-station-back",
                    "label": "from-station-label",
                    "value": from_station["name"],
                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{from_station['name']}</a>",
                })
            elif ticket_data.data.departure_station_name:
                pass_fields["primaryFields"].append({
                    "key": "from-station",
                    "label": "from-station-label",
                    "value": ticket_data.data.departure_station_name,
                    "semantics": {
                        "departureStationName": ticket_data.data.departure_station_name,
                    }
                })

            if ticket_data.data.arrival_station_uic:
                to_station = templatetags.rics.get_station(ticket_data.data.arrival_station_uic, "uic")
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": to_station["name"],
                    "semantics": {
                        "departureLocation": {
                            "latitude": float(to_station["latitude"]),
                            "longitude": float(to_station["longitude"]),
                        },
                        "departureStationName": to_station["name"]
                    }
                })
                maps_link = urllib.parse.urlencode({
                    "q": to_station["name"],
                    "ll": f"{to_station['latitude']},{to_station['longitude']}"
                })
                pass_fields["backFields"].append({
                    "key": "to-station-back",
                    "label": "to-station-label",
                    "value": to_station["name"],
                    "attributedValue": f"<a href=\"https://maps.apple.com/?{maps_link}\">{to_station['name']}</a>",
                })
            elif ticket_data.data.arrival_station_name:
                pass_fields["primaryFields"].append({
                    "key": "to-station",
                    "label": "to-station-label",
                    "value": ticket_data.data.arrival_station_name,
                    "semantics": {
                        "departureStationName": ticket_data.data.arrival_station_name,
                    }
                })

            if ticket_data.data.travel_class:
                pass_fields["auxiliaryFields"].append({
                    "key": "class-code",
                    "label": "class-code-label",
                    "value": f"class-code-{ticket_data.data.travel_class}-label",
                })

            if ticket_data.data.group_leader:
                pass_fields["secondaryFields"].append({
                    "key": "group-leader",
                    "label": "group-leader-label",
                    "value": ticket_data.data.group_leader,
                })

            pass_fields["secondaryFields"].append({
                "key": "validity-start",
                "label": "validity-start-label",
                "dateStyle": "PKDateStyleMedium",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.validity_start.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })
            pass_fields["secondaryFields"].append({
                "key": "validity-end",
                "label": "validity-end-label",
                "dateStyle": "PKDateStyleMedium",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.validity_end.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })
            pass_fields["backFields"].append({
                "key": "issued-date",
                "label": "issued-at-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.issuing_date.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })

            if ticket_data.data.extra_text:
                pass_fields["backFields"].append({
                    "key": "extra-date",
                    "label": "other-data-label",
                    "value": ticket_data.data.extra_text,
                })

        elif isinstance(ticket_data.data, ssb.ns_keycard.Keycard):
            pass_fields["headerFields"].append({
                "key": "card-name",
                "label": "product-label",
                "value": "Keycard",
            })

            if ticket_data.data.station_uic:
                station = templatetags.rics.get_station(ticket_data.data.station_uic, "uic")
                pass_fields["primaryFields"].append({
                    "key": "station",
                    "label": "station-label",
                    "value": station["name"],
                })

            pass_fields["secondaryFields"].append({
                "key": "card-id",
                "label": "card-id-label",
                "value": ticket_data.data.card_id,
            })
            pass_fields["secondaryFields"].append({
                "key": "validity-start",
                "label": "validity-start-label",
                "dateStyle": "PKDateStyleMedium",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.validity_start.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })
            pass_fields["secondaryFields"].append({
                "key": "validity-end",
                "label": "validity-end-label",
                "dateStyle": "PKDateStyleMedium",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.validity_end.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })
            pass_fields["backFields"].append({
                "key": "issued-date",
                "label": "issued-at-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleNone",
                "value": f"{ticket_data.data.issuing_date.isoformat()}T00:00:00Z",
                "ignoresTimeZone": True
            })

            if ticket_data.data.extra_text:
                pass_fields["backFields"].append({
                    "key": "extra-date",
                    "label": "other-data-label",
                    "value": ticket_data.data.extra_text,
                })

        if distributor := ticket_data.envelope.issuer():
            pass_json["organizationName"] = distributor["full_name"]
            if distributor["url"]:
                pass_fields["backFields"].append({
                    "key": "issuing-org",
                    "label": "issuing-organisation-label",
                    "value": distributor["full_name"],
                    "attributedValue": f"<a href=\"{distributor['url']}\">{distributor['full_name']}</a>",
                })
                return_pass_fields["backFields"].append({
                    "key": "issuing-org",
                    "label": "issuing-organisation-label",
                    "value": distributor["full_name"],
                    "attributedValue": f"<a href=\"{distributor['url']}\">{distributor['full_name']}</a>",
                })
            else:
                pass_fields["backFields"].append({
                    "key": "distributor",
                    "label": "issuing-organisation-label",
                    "value": distributor["full_name"],
                })
                return_pass_fields["backFields"].append({
                    "key": "distributor",
                    "label": "issuing-organisation-label",
                    "value": distributor["full_name"],
                })

        if ticket_data.envelope.issuer_rics in RICS_LOGO:
            add_pkp_img(pkp, RICS_LOGO[ticket_data.envelope.issuer_rics], "logo.png")
            have_logo = True
        if ticket_data.envelope.issuer_rics in RICS_BG:
            pass_json["backgroundColor"] = RICS_BG[ticket_data.envelope.issuer_rics]
        if ticket_data.envelope.issuer_rics in RICS_FG:
            pass_json["foregroundColor"] = RICS_FG[ticket_data.envelope.issuer_rics]
        if ticket_data.envelope.issuer_rics in RICS_FG_SECONDARY:
            pass_json["labelColor"] = RICS_FG_SECONDARY[ticket_data.envelope.issuer_rics]

    ticket_url = reverse('ticket', kwargs={"pk": ticket_obj.pk})
    pass_fields["backFields"].append({
        "key": "view-link",
        "label": "more-info-label",
        "value": "",
        "attributedValue": f"<a href=\"{settings.EXTERNAL_URL_BASE}{ticket_url}\">View ticket</a>",
    })
    return_pass_fields["backFields"].append({
        "key": "view-link",
        "label": "more-info-label",
        "value": "",
        "attributedValue": f"<a href=\"{settings.EXTERNAL_URL_BASE}{ticket_url}\">View ticket</a>",
    })

    pass_json[pass_type] = pass_fields
    if return_pass_json:
        return_pass_json[return_pass_type] = return_pass_fields

    for lang, strings in PASS_STRINGS.items():
        pkp.add_file(f"{lang}.lproj/pass.strings", strings.encode("utf-8"))

    if not have_logo:
        add_pkp_img(pkp, "pass/logo.png", "logo.png")

    add_pkp_img(pkp, "pass/icon.png", "icon.png")

    if ticket_obj.ticket_type == models.Ticket.TYPE_DEUTCHLANDTICKET:
        add_pkp_img(pkp, "pass/logo-dt.png", "thumbnail.png")

    public_id = ticket_obj.public_id()
    if has_return:
        pass_json["serialNumber"] = f'{pass_json["serialNumber"]}:outbound'
        return_pass_json["serialNumber"] = f'{return_pass_json["serialNumber"]}:return'

        if part == "outbound":
            pkp.add_file("pass.json", json.dumps(pass_json).encode("utf-8"))
            pkp.sign()

            return f"{public_id}_outbound.pkpass", [
                (f"{public_id}_outbound.pkpass", pkp.get_buffer())
            ]
        elif part == "return":
            pkp.add_file("pass.json", json.dumps(return_pass_json).encode("utf-8"))
            pkp.sign()

            return f"{public_id}_return.pkpass", [
                (f"{public_id}_return.pkpass", pkp.get_buffer())
            ]
        else:
            pkp.add_file("pass.json", json.dumps(pass_json).encode("utf-8"))
            pkp.sign()
            buf1 = pkp.get_buffer()

            pkp.add_file("pass.json", json.dumps(return_pass_json).encode("utf-8"))
            pkp.sign()
            buf2 = pkp.get_buffer()

            return f"{public_id}.pkpasses", [
                (f"{public_id}_outbound.pkpass", buf1),
                (f"{public_id}_return.pkpass", buf2)
            ]
    else:
        pkp.add_file("pass.json", json.dumps(pass_json).encode("utf-8"))
        pkp.sign()

        return f"{public_id}.pkpass", [
            (f"{public_id}.pkpass", pkp.get_buffer())
        ]


def make_pkpass(ticket_obj: "models.Ticket", part: typing.Optional[str] = None):
    file_name, files = make_pkpass_file(ticket_obj, part)

    if len(files) == 1:
        response = HttpResponse()
        response['Content-Type'] = "application/vnd.apple.pkpass"
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        response.write(files[0][1])
        return response
    else:
        multi_pass = pkpass.MultiPKPass()
        for _, file_contents in files:
            multi_pass.add_pkpass(file_contents)
        response = HttpResponse()
        response['Content-Type'] = "application/vnd.apple.pkpasses"
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        response.write(multi_pass.get_buffer())
        return response

PASS_STRINGS = {
    "en": """
"product-label" = "Product";
"ticket-id-label" = "Ticket ID";
"card-id-label" = "Card ID";
"more-info-label" = "More info";
"product-organisation-label" = "Product Organisation";
"issuing-organisation-label" = "Issuing Organisation";
"ticketing-organisation-label" = "Ticketing Organisation";
"validity-start-label" = "Valid from";
"validity-end-label" = "Valid until";
"validity-end-change" = "Validity extended to %@";
"issued-at-label" = "Issued at";
"passenger-label" = "Passenger";
"class-code-label" = "Class";
"class-code-first-label" = "1st";
"class-code-1-label" = "1st";
"class-code-second-label" = "2nd";
"class-code-2-label" = "2nd";
"reduction-card-label" = "Discount card";
"date-of-birth-label" = "Date of birth";
"month-of-birth-label" = "Birth month";
"year-of-birth-label" = "Birth year";
"country-of-residence-label" = "Country of residence";
"passport-number-label" = "Passport number";
"from-station-label" = "From";
"to-station-label" = "To";
"station-label" = "Station";
"product-id-label" = "Ticket type";
"valid-region-label" = "Validity";
"return-included-label" = "Return included";
"return-included-yes" = "Yes";
"return-included-no" = "No";
"railcard-number" = "Railcard number";
"departure-date-label" = "Departure date";
"departure-time-label" = "Departure";
"arrival-time-label" = "Arrival";
"train-number-label" = "Train number";
"coach-number-label" = "Coach";
"seat-number-label" = "Seat";
"price-label" = "Price";
"product-validity-outward-date-label" = "Outward validity - date";
"product-validity-outward-time-label" = "Outward validity - time";
"product-validity-return-date-label" = "Return validity - date";
"product-validity-return-time-label" = "Return validity - time";
"product-break-of-journey-outward-label" = "Break of journey - outward";
"product-break-of-journey-return-label" = "Break of journey - return";
"product-conditions-label" = "Conditions";
"product-changes-label" = "Changes to travel plans";
"product-refunds-label" = "Refunds";
"carrier-label" = "Carrier";
"reference-num-label" = "Reference number";
"other-data-label" = "Other data";
"travel-via-all-label" = "Travel must be made via all of";
"travel-via-any-label" = "Travel must be made via any of";
"travel-via-excl-label" = "Travel must not be made via";
"travel-inc-toc-label" = "Travel must include a service operated by";
"travel-excl-toc-label" = "Travel must not include a service operated by";
"route-label" = "Route";
"group-ticket-label" = "Group ticket";
"group-leader-label" = "Group leader";
""",
    "cy": """
"product-label" = "Cynnyrch";
"ticket-id-label" = "Rhif Tocyn";
"card-id-label" = "Rhif Cerdyn";
"more-info-label" = "Gwybodaeth ychwanegol";
"product-organisation-label" = "Cynnyrchgwni";
"issuing-organisation-label" = "Cwni dyddori";
"ticketing-organisation-label" = "Cwni tocynnu";
"validity-start-label" = "Dilys o";
"validity-end-label" = "Dilys tan";
"validity-end-change" = "Wedi ystynnedu tan %@";
"issued-at-label" = "Dyddorwyd am";
"passenger-label" = "Teithiwr";
"class-code-label" = "Dosbarth";
"class-code-first-label" = "1af";
"class-code-1-label" = "1af";
"class-code-second-label" = "2ail";
"class-code-2-label" = "2ail";
"reduction-card-label" = "Cerdyn gostwng";
"date-of-birth-label" = "Dyddiad genni";
"month-of-birth-label" = "Mîs genni";
"year-of-birth-label" = "Blwyddyn genni";
"country-of-residence-label" = "Gwlad breswylio";
"passport-number-label" = "Rhif Pasbort";
"from-station-label" = "O";
"to-station-label" = "I";
"station-label" = "Gorsaf";
"product-id-label" = "Math tocyn";
"valid-region-label" = "Dilysrwydd";
"return-included-label" = "Gyda dychweldaith?";
"return-included-yes" = "Iê";
"return-included-no" = "Na";
"railcard-number" = "Rhif Railcard";
"departure-date-label" = "Dyddiad teithio";
"departure-time-label" = "Ymadawiad";
"arrival-time-label" = "Cyrrhaeddiad";
"train-number-label" = "Rhif y trên";
"coach-number-label" = "Cerbyd";
"seat-number-label" = "Sedd";
"price-label" = "Pris";
"product-validity-outward-date-label" = "Dilysrwydd alladaith - dyddiad";
"product-validity-outward-time-label" = "Dilysrwydd alladaith - amser";
"product-validity-return-date-label" = "Dilysrwydd dychweldaith - dyddiad";
"product-validity-return-time-label" = "Dilysrwydd dychweldaith - amser";
"product-break-of-journey-outward-label" = "Toriad taith - allandaith";
"product-break-of-journey-return-label" = "Toriad taith - dychweldaith";
"product-conditions-label" = "Telerau";
"product-changes-label" = "Newidiadau i gynlluniau teithio";
"product-refunds-label" = "Ad-daliadau";
"carrier-label" = "Cludwr";
"reference-num-label" = "Cyfeirnod";
"other-data-label" = "Data arall";
"travel-via-all-label" = "Rhaid teithio trwy pob un o";
"travel-via-any-label" = "Rhaid teithio twry un o";
"travel-via-excl-label" = "Ni allai teithio trwy";
"travel-inc-toc-label" = "Rhaid i'r daith cynnwys gwasanaeth";
"travel-excl-toc-label" = "Ni all y daith cynnwys gwasanaeth";
"route-label" = "Llwybr";
"group-ticket-label" = "Tocyn grwp";
"group-leader-label" = "Prifdeithiwr";
""",
    "de": """
"product-label" = "Produkt";
"ticket-id-label" = "Ticket-ID";
"card-id-label" = "Kartennummer";
"more-info-label" = "Mehr Infos";
"product-organisation-label" = "Produktorganisation";
"issuing-organisation-label" = "Ausstellende Organisation";
"ticketing-organisation-label" = "Ticketverkaufsorganisation";
"validity-start-label" = "Gültig vom";
"validity-end-label" = "Gültig bis";
"validity-end-change" = "Verlängert bis %@";
"issued-at-label" = "Ausgestellt am";
"passenger-label" = "Fahrgast";
"class-code-label" = "Klasse";
"class-code-first-label" = "1.";
"class-code-1-label" = "1.";
"class-code-second-label" = "2.";
"class-code-2-label" = "2.";
"reduction-card-label" = "Bahncard";
"date-of-birth-label" = "Geburtsdatum";
"month-of-birth-label" = "Geburtsmonat";
"year-of-birth-label" = "Geburtsjahr";
"country-of-residence-label" = "Land des Wohnsitzes";
"passport-number-label" = "Passnummer";
"from-station-label" = "Von";
"to-station-label" = "Nach";
"station-label" = "Bahnhof";
"product-id-label" = "Tickettyp";
"valid-region-label" = "Gültigkeit";
"return-included-label" = "Rückfahrt inklusive";
"return-included-yes" = "Ja";
"return-included-no" = "Nein";
"railcard-number" = "Railcard-Nummer";
"departure-date-label" = "Datum";
"departure-time-label" = "Abfahrt";
"arrival-time-label" = "Ankunft";
"train-number-label" = "Zug nr.";
"coach-number-label" = "Waggon";
"seat-number-label" = "Sitzpl.";
"price-label" = "Preis";
"product-validity-outward-date-label" = "Hinfahrt Gültigkeit - Datum";
"product-validity-outward-time-label" = "Hinfahrt Gültigkeit - Zeit";
"product-validity-return-date-label" = "Ruckfahrt Gültigkeit - Datum";
"product-validity-return-time-label" = "Ruckfahrt Gültigkeit - Zeit";
"product-break-of-journey-outward-label" = "Reisepause - Hinfahrt";
"product-break-of-journey-return-label" = "Reisepause - Ruckfahrt";
"product-conditions-label" = "Bedingungen";
"product-changes-label" = "Änderungen";
"product-refunds-label" = "Erstattungen";
"carrier-label" = "Verkehrsbetrieb";
"reference-num-label" = "Referenznummer";
"other-data-label" = "Andere Daten";
"travel-via-all-label" = "Gültige Fahrt nur über alle";
"travel-via-any-label" = "Gültige Fahrt nur über mindestens eine";
"travel-via-excl-label" = "Gültige Fahrt nich über";
"travel-inc-toc-label" = "Gültige Fahrt nur mit einen Dienst von";
"travel-excl-toc-label" = "Gültige Fahrt nicht mit Dienste von";
"route-label" = "Route";
"group-ticket-label" = "Gruppenkarte";
"group-leader-label" = "Hauptfahrgast";
""",
    "nl": """
"product-label" = "Product";
"ticket-id-label" = "Ticket-ID";
"card-id-label" = "Kaart-ID";
"more-info-label" = "Meer info";
"product-organisation-label" = "Productorganisatie";
"issuing-organisation-label" = "Uitgevende Organisatie";
"ticketing-organisation-label" = "Ticketorganisatie";
"validity-start-label" = "Geldig van";
"validity-end-label" = "Geldig tot";
"validity-end-change" = "Geldigheid verlengd tot %@";
"issued-at-label" = "Uitgegeven om";
"passenger-label" = "Reiziger";
"class-code-label" = "Klasse";
"class-code-first-label" = "1e";
"class-code-1-label" = "1e";
"class-code-second-label" = "2e";
"class-code-2-label" = "2e";
"reduction-card-label" = "Kortingskaart";
"date-of-birth-label" = "Geboortedatum";
"month-of-birth-label" = "Geboortemaand";
"year-of-birth-label" = "Geboortejaar";
"country-of-residence-label" = "Woonachtig in land";
"passport-number-label" = "Paspoortnummer";
"from-station-label" = "Van";
"to-station-label" = "Naar";
"station-label" = "Station";
"product-id-label" = "Tickettype";
"valid-region-label" = "Geldigheid";
"return-included-label" = "Inclusief retour";
"return-included-yes" = "Ja";
"return-included-no" = "Nee";
"railcard-number" = "Railcard-nummer";
"departure-date-label" = "Vertrekdatum";
"departure-time-label" = "Vertrek";
"arrival-time-label" = "Aankomst";
"train-number-label" = "Treinnummer";
"coach-number-label" = "Rijtuig";
"seat-number-label" = "Stoel";
"price-label" = "Prijs";
"product-validity-outward-date-label" = "Geldigheid heenrit - datum";
"product-validity-outward-time-label" = "Geldigheid heenrit - tijd";
"product-validity-return-date-label" = "Geldigheid terugrit - datum";
"product-validity-return-time-label" = "Geldigheid terugrit - tijd";
"product-break-of-journey-outward-label" = "Ritonderbreking - heenrit";
"product-break-of-journey-return-label" = "Ritonderbreking - terugrit";
"product-conditions-label" = "Voorwaarden";
"product-changes-label" = "Wijzigingen aan het reisplan";
"product-refunds-label" = "Restitutie";
"carrier-label" = "Vervoerder";
"reference-num-label" = "Referentienummer";
"other-data-label" = "Andere gegevens";
"travel-via-all-label" = "Reis moet gemaakt worden via alle van";
"travel-via-any-label" = "Reis moet gemaakt worden via tenminste één van";
"travel-via-excl-label" = "Reis mag niet gemaakt worden via";
"travel-inc-toc-label" = "Reis moet vervoer bevatten uitgevoerd door";
"travel-excl-toc-label" = "Reis mag geen vervoer bevatten uitgevoerd door";
"route-label" = "Route";
"""
}

RICS_LOGO = {
    80: "pass/logo-db.png",
    1080: "pass/logo-db.png",
    1088: "pass/logo-sncb.png",
    1084: "pass/logo-ns.png",
    1154: "pass/logo-cd.png",
    1155: "pass/logo-mav.png",
    1156: "pass/logo-zssk.png",
    1179: "pass/logo-szpp.png",
    1181: "pass/logo-oebb.png",
    1182: "pass/logo-cfl.png",
    1184: "pass/logo-ns.png",
    1186: "pass/logo-dsb.png",
    1251: "pass/logo-pkp-ic.png",
    3018: "pass/logo-thalys.png",
    3076: "pass/logo-transdev.png",
    3153: "pass/logo-wl.png",
    3243: "pass/logo-ustra.png",
    3268: "pass/logo-graz.png",
    3306: "pass/logo-vor.png",
    3316: "pass/logo-avg.png",
    3453: "pass/logo-mvb.png",
    3497: "pass/logo-rvv.png",
    3509: "pass/logo-ret.png",
    3591: "pass/logo-akn.png",
    3606: "pass/logo-qbuzz.png",
    5008: "pass/logo-vrn.png",
    5173: "pass/logo-nasa.png",
    5177: "pass/logo-fribus.png",
    5188: "pass/logo-es.png",
    5197: "pass/logo-avv.png",
    5211: "pass/logo-vetter.png",
    5217: "pass/logo-bremerhaven.png",
    5245: "pass/logo-wvv.png",
    8999: "pass/logo-connexxion.png",
    9901: "pass/logo-interrail.png",
}

RICS_BG = {
    1084: "rgb(255, 201, 23)",
    1184: "rgb(255, 201, 23)",
    3018: "rgb(175, 22, 52)",
    3453: "rgb(1, 142, 74)",
    3497: "rgb(20, 24, 26)",
    5188: "rgb(64, 0, 44)",
    8999: "rgb(11, 130, 143)",
}

RICS_FG = {
    1084: "rgb(7, 7, 33)",
    1184: "rgb(7, 7, 33)",
    3018: "rgb(255, 255, 255)",
    3453: "rgb(255, 255, 255)",
    3497: "rgb(255, 255, 255)",
    3606: "rgb(0, 70, 84)",
    5188: "rgb(255, 255, 255)",
    8999: "rgb(255, 255, 255)",
}

RICS_FG_SECONDARY = {
    1084: "rgb(32, 32, 55)",
    1184: "rgb(32, 32, 55)",
    3018: "rgb(255, 255, 255)",
    3153: "rgb(227, 0, 21)",
    3243: "rgb(120, 180, 30)",
    3268: "rgb(67, 165, 0)",
    3306: "rgb(128, 204, 40)",
    3453: "rgb(255, 255, 255)",
    3497: "rgb(149, 200, 125)",
    3606: "rgb(247, 147, 48)",
    5188: "rgb(255, 54, 0)",
    5245: "rgb(211, 2, 64)",
    8999: "rgb(226, 1, 112)",
}

UIC_NAME_LOGO = {
    "BMK": "pass/logo-kt.png",
}

VDV_ORG_ID_LOGO = {
    35: "pass/logo-hvv.png",
    36: "pass/logo-rmv.png",
    49: "pass/logo-swk.png",
    57: "pass/logo-dsw.png",
    70: "pass/logo-vrr.png",
    77: "pass/logo-wt.png",
    102: "pass/logo-vrs.png",
    103: "pass/logo-swb.png",
    6003: "pass/logo-kvsh.png",
    6055: "pass/logo-mdv.png",
    6060: "pass/logo-vvo.png",
    6072: "pass/logo-avv2.png",
    6073: "pass/logo-aseag.png",
    6074: "pass/logo-vgn.png",
    6096: "pass/logo-vmt.png",
    6100: "pass/logo-vbb.png",
    6150: "pass/logo-hnv.png",
    6212: "pass/logo-vrs.png",
    6234: "pass/logo-vvs.png",
    6292: "pass/logo-mvg.png",
    6310: "pass/logo-svv.png",
    6377: "pass/logo-db.png",
    6395: "pass/logo-ssw.png",
    6425: "pass/logo-db.png",
    6441: "pass/logo-kvg.png",
    6478: "pass/logo-bw.png",
    6491: "pass/logo-rnv.png",
    6496: "pass/logo-naldo.png",
    6517: "pass/logo-rnn.png",
    6613: "pass/logo-arriva.png",
    6665: "pass/logo-rsag.png",
    6671: "pass/logo-ewse.png",
    6691: "pass/logo-vgi.png",
    6861: "pass/logo-nst.png",
}

VDV_ORG_ID_BG = {
    6517: "rgb(0, 79, 159)"
}

VDV_ORG_ID_FG = {
    6072: "rgb(67, 67, 67)",
    6517: "rgb(255, 255, 255)",
}

VDV_ORG_ID_FG_SECONDARY = {
    49: "rgb(226, 1, 26)",
    6072: "rgb(181, 9, 127)",
    6310: "rgb(12, 156, 58)",
    6517: "rgb(255, 204, 2)",
    6691: "rgb(0, 56, 116)",
}

RSP_ORG_LOGO = {
    "TT": "pass/logo-tt.png",
    "CS": "pass/logo-cs.png",
    "RE": "pass/logo-re.png",
}

BC_STRIP_IMG = {
    "BahnCard 50 Herbst Aktion 2024 (1. Klasse)": "bahncard/AKTIONSBAHNCARD501KLASSE.png",
    "BahnCard 50 Herbst Aktion 2024 (2. Klasse)": "bahncard/AKTIONSBAHNCARD502KLASSE.png",
    "My BahnCard 25 (1. Klasse)": "bahncard/MYBAHNCARD251KLASSE.png",
    "My BahnCard 25 (2. Klasse)": "bahncard/MYBAHNCARD252KLASSE.png",
    "My BahnCard 50 (1. Klasse)": "bahncard/MYBAHNCARD501KLASSE.png",
    "My BahnCard 50 (2. Klasse)": "bahncard/MYBAHNCARD502KLASSE.png",
    "BahnCard 25 (1. Klasse)": "bahncard/BAHNCARD251KLASSE.png",
    "BahnCard 25 (2. Klasse)": "bahncard/BAHNCARD252KLASSE.png",
    "BahnCard 50 (1. Klasse)": "bahncard/BAHNCARD501KLASSE.png",
    "BahnCard 50 (2. Klasse)": "bahncard/BAHNCARD502KLASSE.png",
    "Jugend BahnCard 25": "bahncard/JUGENDBAHNCARD25BAHN.png",
}