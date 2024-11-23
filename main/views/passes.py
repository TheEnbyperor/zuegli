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
from main import forms, models, ticket, pkpass, vdv, aztec, templatetags, apn, gwallet, rsp, elb


def index(request):
    ticket_bytes = None
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
                                if ticket_bytes:
                                    break
                                for pdf_image in pdf.get_page_images(page_index):
                                    pdf_image = pdf.extract_image(pdf_image[0])
                                    try:
                                        ticket_bytes = aztec.decode(pdf_image["image"])
                                    except aztec.AztecError:
                                        continue
                                    else:
                                        break

                            if not ticket_bytes:
                                image_form.add_error("ticket", f"Failed to find any Aztec codes in the PDF")

    else:
        image_form = forms.TicketUploadForm()

    if ticket_bytes:
        try:
            ticket_data = ticket.parse_ticket(ticket_bytes,
                                              request.user.account if request.user.is_authenticated else None)
        except ticket.TicketError as e:
            error = {
                "title": e.title,
                "message": e.message,
                "exception": e.exception,
                "ticket_contents": ticket_bytes.hex()
            }
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
            return redirect('ticket', pk=ticket_obj.id)

    return render(request, "main/index.html", {
        "image_form": image_form,
        "error": error,
    })


def view_ticket(request, pk):
    ticket_obj = get_object_or_404(models.Ticket, id=pk)
    gwallet_url = gwallet.create_jwt_link(ticket_obj)

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
        "photo_upload_forms": photo_upload_forms
    })


def pass_photo_thumbnail(ticket_obj: models.Ticket, size, padding):
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
    img_1x = storages["staticfiles"].open(f"{img_name}.{img_name_ext}", "rb").read()
    pkp.add_file(f"{pass_path}.{pass_path_ext}", img_1x)
    img_2x = storages["staticfiles"].open(f"{img_name}@2x.{img_name_ext}", "rb").read()
    pkp.add_file(f"{pass_path}@2x.{pass_path_ext}", img_2x)
    img_3x = storages["staticfiles"].open(f"{img_name}@3x.{img_name_ext}", "rb").read()
    pkp.add_file(f"{pass_path}@3x.{pass_path_ext}", img_3x)


def ticket_pkpass(request, pk):
    ticket_obj: models.Ticket = get_object_or_404(models.Ticket, id=pk)
    return make_pkpass(ticket_obj)


def make_pkpass(ticket_obj: models.Ticket, part: typing.Optional[str] = None):
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

        if ticket_data.flex:
            pass_json["voided"] = not ticket_data.flex.data["issuingDetail"]["activated"]

            if ticket_data.flex.data["issuingDetail"].get("issuerName") in UIC_NAME_LOGO:
                add_pkp_img(pkp, UIC_NAME_LOGO[ticket_data.flex.data["issuingDetail"]["issuerName"]], "logo.png")
                have_logo = True

            if len(ticket_data.flex.data["transportDocument"]) >= 1:
                document_type, document = ticket_data.flex.data["transportDocument"][0]["ticket"]
                if document_type == "openTicket":
                    validity_start = templatetags.rics.rics_valid_from(document, issued_at)
                    validity_end = templatetags.rics.rics_valid_until(document, issued_at)

                    pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if ticket_obj.ticket_type != ticket_obj.TYPE_DEUTCHLANDTICKET:
                        pass_json["relevantDate"] = validity_start.strftime("%Y-%m-%dT%H:%M:%SZ")

                    if "fromStationNum" in document and "toStationNum" in document:
                        pass_type = "boardingPass"
                        pass_fields["transitType"] = "PKTransitTypeTrain"

                        from_station = templatetags.rics.get_station(document["fromStationNum"], document)
                        to_station = templatetags.rics.get_station(document["toStationNum"], document)

                        if "classCode" in document:
                            pass_fields["auxiliaryFields"].append({
                                "key": "class-code",
                                "label": "class-code-label",
                                "value": f"class-code-{document['classCode']}-label",
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
                        elif "fromStationNameUTF8" in document:
                            pass_fields["primaryFields"].append({
                                "key": "from-station",
                                "label": "from-station-label",
                                "value": document["fromStationNameUTF8"],
                                "semantics": {
                                    "departureStationName": document["fromStationNameUTF8"]
                                }
                            })
                        elif "fromStationIA5" in document:
                            pass_fields["primaryFields"].append({
                                "key": "from-station",
                                "label": "from-station-label",
                                "value": document["fromStationIA5"],
                                "semantics": {
                                    "departureStationName": document["fromStationIA5"]
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
                        elif "toStationNameUTF8" in document:
                            pass_fields["primaryFields"].append({
                                "key": "to-station",
                                "label": "to-station-label",
                                "value": document["toStationNameUTF8"],
                                "semantics": {
                                    "destinationStationName": document["toStationNameUTF8"]
                                }
                            })
                        elif "toStationIA5" in document:
                            pass_fields["primaryFields"].append({
                                "key": "to-station",
                                "label": "to-station-label",
                                "value": document["toStationIA5"],
                                "semantics": {
                                    "destinationStationName": document["toStationIA5"]
                                }
                            })
                    else:
                        if "classCode" in document:
                            pass_fields["auxiliaryFields"].append({
                                "key": "class-code",
                                "label": "class-code-label",
                                "value": f"class-code-{document['classCode']}-label",
                            })

                    if len(document.get("tariffs")) >= 1:
                        tariff = document["tariffs"][0]
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

                        for card in tariff.get("reductionCard", []):
                            pass_fields["auxiliaryFields"].append({
                                "key": "reduction-card",
                                "label": "reduction-card-label",
                                "value": card["cardName"]
                            })

                    pass_fields["backFields"].append({
                        "key": "return-included",
                        "label": "return-included-label",
                        "value": "return-included-yes" if document["returnIncluded"] else "return-included-no",
                    })

                    if "productIdIA5" in document:
                        pass_fields["backFields"].append({
                            "key": "product-id",
                            "label": "product-id-label",
                            "value": document["productIdIA5"],
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

                    if "validRegionDesc" in document:
                        pass_fields["backFields"].append({
                            "key": "valid-region",
                            "label": "valid-region-label",
                            "value": document["validRegionDesc"],
                        })

                    if "validRegion" in document and document["validRegion"][0][0] == "trainLink":
                        train_link = document["validRegion"][0][1]
                        departure_time = templatetags.rics.rics_departure_time(train_link, issued_at)
                        pass_json["relevantDate"] = departure_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                        train_number = train_link["trainIA5"] or str(train_link["trainNum"])
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
                        pass_json["locations"] = []
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

                    if "returnDescription" in document:
                        return_document = document["returnDescription"]
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

                            from_station = templatetags.rics.get_station(return_document["fromStationNum"], document)
                            to_station = templatetags.rics.get_station(return_document["toStationNum"], document)

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

                        if "validReturnRegion" in return_document and return_document["validReturnRegion"][0][
                            0] == "trainLink":
                            train_link = return_document["validReturnRegion"][0][1]
                            departure_time = templatetags.rics.rics_departure_time(train_link, issued_at)
                            return_pass_json["relevantDate"] = departure_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                            train_number = train_link["trainIA5"] or str(train_link["trainNum"])
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

                elif document_type == "customerCard":
                    validity_start = templatetags.rics.rics_valid_from_date(document)
                    validity_end = templatetags.rics.rics_valid_until_date(document)

                    pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")

                    if "cardTypeDescr" in document:
                        pass_fields["headerFields"].append({
                            "key": "product",
                            "label": "product-label",
                            "value": document["cardTypeDescr"]
                        })
                        pass_fields["backFields"].append({
                            "key": "product-back",
                            "label": "product-label",
                            "value": document["cardTypeDescr"]
                        })

                    if "cardIdIA5" in document:
                        pass_fields["secondaryFields"].append({
                            "key": "card-id",
                            "label": "card-id-label",
                            "value": document["cardIdIA5"],
                        })
                    elif "cardIdNum" in document:
                        pass_fields["secondaryFields"].append({
                            "key": "card-id",
                            "label": "card-id-label",
                            "value": str(document["cardIdNum"]),
                        })

                    if "classCode" in document:
                        pass_fields["secondaryFields"].append({
                            "key": "class-code",
                            "label": "class-code-label",
                            "value": f"class-code-{document['classCode']}-label",
                        })

                    if validity_start:
                        pass_json["relevantDate"] = validity_start.strftime("%Y-%m-%dT%H:%M:%SZ")
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

                elif document_type == "pass":
                    validity_start = templatetags.rics.rics_valid_from(document, issued_at)
                    validity_end = templatetags.rics.rics_valid_until(document, issued_at)

                    pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")

                    if "passType" in document:
                        if document["passType"] == 1:
                            product_name = "Eurail Global Pass"
                        elif document["passType"] == 2:
                            product_name = "Interrail Global Pass"
                        elif document["passType"] == 3:
                            product_name = "Interrail One Country Pass"
                        elif document["passType"] == 4:
                            product_name = "Eurail One Country Pass"
                        elif document["passType"] == 5:
                            product_name = "Eurail/Interrail Emergency ticket"
                        else:
                            product_name = f"Pass type {document['passType']}"
                    elif "passDescription" in document:
                        product_name = document["passDescription"]
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
                pass_fields["primaryFields"].append({
                    "key": "passenger",
                    "label": "passenger-label",
                    "value": ticket_data.cd_ut.name,
                })

        elif ticket_data.oebb_99:
            pass_json["expirationDate"] = ticket_data.oebb_99.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
            pass_json["relevantDate"] = ticket_data.oebb_99.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            pass_fields["headerFields"].append({
                "key": "train-number",
                "label": "train-number-label",
                "value": str(ticket_data.oebb_99.train_number),
            })
            pass_fields["secondaryFields"].append({
                "key": "validity-start",
                "label": "validity-start-label",
                "dateStyle": "PKDateStyleMedium",
                "timeStyle": "PKDateStyleNone",
                "value": ticket_data.oebb_99.validity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            pass_fields["backFields"].append({
                "key": "validity-start-back",
                "label": "validity-start-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleFull",
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
            pass_fields["backFields"].append({
                "key": "validity-end-back",
                "label": "validity-end-label",
                "dateStyle": "PKDateStyleFull",
                "timeStyle": "PKDateStyleFull",
                "value": ticket_data.oebb_99.validity_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
                pass_fields["primaryFields"].append({
                    "key": "passenger",
                    "label": "passenger-label",
                    "value": f"{elm.forename}\n{elm.surname}",
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

        if ticket_data.ticket.product_org_id in VDV_ORG_ID_LOGO:
            add_pkp_img(pkp, VDV_ORG_ID_LOGO[ticket_data.ticket.product_org_id], "logo.png")
            have_logo = True
        elif ticket_data.ticket.product_org_id == 3000 and ticket_data.ticket.ticket_org_id in VDV_ORG_ID_LOGO:
            add_pkp_img(pkp, VDV_ORG_ID_LOGO[ticket_data.ticket.ticket_org_id], "logo.png")
            have_logo = True
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
                "auxiliaryFields": [],
                "secondaryFields": [{
                    "key": "travel-class",
                    "label": "class-code-label",
                    "value": "class-code-second-label" if ticket_data.data.standard_class else "class-code-first-label",
                }],
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
                    "value": f"£{ticket_data.data.purchase_data.price}"
                }])

            for i, reservation in enumerate(ticket_data.data.reservations):
                pass_fields["auxiliaryFields"].append({
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

            if ticket_type := rsp.ticket_data.get_ticket_type(ticket_data.data.fare_label):
                pass_fields["secondaryFields"].append({
                    "key": "product",
                    "label": "product-label",
                    "value": ticket_type.ticket_type_name,
                })
                if ticket_type.validity:
                    pass_fields["backFields"].extend([{
                        "key": "product-validity-outward-date",
                        "label": "product-validity-outward-date-label",
                        "attributedValue": ticket_type.validity.day_outward.replace('title=""', ""),
                    }, {
                        "key": "product-validity-outward-time",
                        "label": "product-validity-outward-time-label",
                        "attributedValue": ticket_type.validity.time_outward.replace('title=""', ""),
                    }, {
                        "key": "product-validity-return-date",
                        "label": "product-validity-return-date-label",
                        "attributedValue": ticket_type.validity.day_return.replace('title=""', ""),
                    }, {
                        "key": "product-validity-return-time",
                        "label": "product-validity-return-time-label",
                        "attributedValue": ticket_type.validity.time_return.replace('title=""', ""),
                    }])
                if ticket_type.break_of_journey:
                    pass_fields["backFields"].extend([{
                        "key": "product-break-of-journey-outward",
                        "label": "product-break-of-journey-outward-label",
                        "attributedValue": ticket_type.break_of_journey.outward_note.replace('title=""', ""),
                    }, {
                        "key": "product-break-of-journey-return",
                        "label": "product-break-of-journey-return-label",
                        "attributedValue": ticket_type.break_of_journey.return_note.replace('title=""', ""),
                    }])
                if ticket_type.conditions:
                    pass_fields["backFields"].append({
                        "key": "product-conditions",
                        "label": "product-conditions-label",
                        "attributedValue": ticket_type.conditions.replace('title=""', ""),
                    })
                if ticket_type.changes_to_travel_plans:
                    pass_fields["backFields"].append({
                        "key": "product-changes",
                        "label": "product-changes-label",
                        "attributedValue": ticket_type.changes_to_travel_plans.replace('title=""', ""),
                    })
                if ticket_type.refunds:
                    pass_fields["backFields"].append({
                        "key": "product-refunds",
                        "label": "product-refunds-label",
                        "attributedValue": ticket_type.refunds.replace('title=""', ""),
                    })

            if ticket_data.issuer_id in RSP_ORG_LOGO:
                add_pkp_img(pkp, RSP_ORG_LOGO[ticket_data.issuer_id], "logo.png")
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
        from_station = templatetags.rics.get_station(ticket_data.data.departure_station, "benerail")
        to_station = templatetags.rics.get_station(ticket_data.data.arrival_station, "benerail")

        pass_json["expirationDate"] = validity_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        pass_json["relevantDate"] = departure_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        pass_json["locations"].append({
            "latitude": float(from_station["latitude"]),
            "longitude": float(from_station["longitude"]),
            "relevantText": from_station["name"]
        })
        from_station_maps_link = urllib.parse.urlencode({
            "q": from_station["name"],
            "ll": f"{from_station['latitude']},{from_station['longitude']}"
        })
        pass_json["locations"].append({
            "latitude": float(to_station["latitude"]),
            "longitude": float(to_station["longitude"]),
            "relevantText": to_station["name"]
        })
        to_station_maps_link = urllib.parse.urlencode({
            "q": to_station["name"],
            "ll": f"{to_station['latitude']},{to_station['longitude']}"
        })

        pass_fields = {
            "transitType": "PKTransitTypeTrain",
            "headerFields": [{
                "key": "departure-date",
                "label": "departure-date-label",
                "value": departure_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "dateStyle": "PKDateStyleMedium",
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
                "value": str(ticket_data.data.booking_number),
            }]
        }
        pass_json["barcodes"] = [{
            "format": "PKBarcodeFormatAztec",
            "message": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
            "messageEncoding": "iso-8859-1",
            "altText": f"{ticket_data.data.pnr} {ticket_data.data.sequence_number}"
        }]
        add_pkp_img(pkp, "pass/logo-eurostar.png", "logo.png")
        have_logo = True

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

    if has_return:
        pass_json["serialNumber"] = f'{pass_json["serialNumber"]}:outbound'
        return_pass_json["serialNumber"] = f'{return_pass_json["serialNumber"]}:return'

        if part == "outbound":
            pkp.add_file("pass.json", json.dumps(pass_json).encode("utf-8"))
            pkp.sign()

            response = HttpResponse()
            response['Content-Type'] = "application/vnd.apple.pkpass"
            response['Content-Disposition'] = f'attachment; filename="{ticket_obj.pk}.pkpass"'
            response.write(pkp.get_buffer())
            return response
        elif part == "return":
            pkp.add_file("pass.json", json.dumps(return_pass_json).encode("utf-8"))
            pkp.sign()

            response = HttpResponse()
            response['Content-Type'] = "application/vnd.apple.pkpass"
            response['Content-Disposition'] = f'attachment; filename="{ticket_obj.pk}.pkpass"'
            response.write(pkp.get_buffer())
            return response
        else:
            multi_pass = pkpass.MultiPKPass()

            pkp.add_file("pass.json", json.dumps(pass_json).encode("utf-8"))
            pkp.sign()
            multi_pass.add_pkpass(pkp)

            pkp.add_file("pass.json", json.dumps(return_pass_json).encode("utf-8"))
            pkp.sign()
            multi_pass.add_pkpass(pkp)

            response = HttpResponse()
            response['Content-Type'] = "application/vnd.apple.pkpasses"
            response['Content-Disposition'] = f'attachment; filename="{ticket_obj.pk}.pkpasses"'
            response.write(multi_pass.get_buffer())
            return response
    else:
        pkp.add_file("pass.json", json.dumps(pass_json).encode("utf-8"))
        pkp.sign()

        response = HttpResponse()
        response['Content-Type'] = "application/vnd.apple.pkpass"
        response['Content-Disposition'] = f'attachment; filename="{ticket_obj.pk}.pkpass"'
        response.write(pkp.get_buffer())
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
"product-id-label" = "Ticket type";
"valid-region-label" = "Validity";
"return-included-label" = "Return included";
"return-included-yes" = "Yes";
"return-included-no" = "No";
"railcard-number" = "Railcard number";
"departure-date-label" = "Departure date";
"departure-time-label" = "Departure";
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
"product-id-label" = "Tickettyp";
"valid-region-label" = "Gültigkeit";
"return-included-label" = "Rückfahrt inklusive";
"return-included-yes" = "Ja";
"return-included-no" = "Nein";
"railcard-number" = "Railcard-Nummer";
"departure-date-label" = "Datum";
"departure-time-label" = "Abfahrt";
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
"""
}

RICS_LOGO = {
    80: "pass/logo-db.png",
    1080: "pass/logo-db.png",
    1088: "pass/logo-sncb.png",
    1181: "pass/logo-oebb.png",
    1084: "pass/logo-ns.png",
    1154: "pass/logo-cd.png",
    1156: "pass/logo-zssk.png",
    1184: "pass/logo-ns.png",
    1186: "pass/logo-dsb.png",
    1251: "pass/logo-pkp-ic.png",
    3076: "pass/logo-transdev.png",
    3509: "pass/logo-ret.png",
    3591: "pass/logo-akn.png",
    5008: "pass/logo-vrn.png",
    5177: "pass/logo-fribus.png",
    5197: "pass/logo-avv.png",
    5217: "pass/logo-bremerhaven.png",
    9901: "pass/logo-interrail.png",
}

UIC_NAME_LOGO = {
    "BMK": "pass/logo-kt.png",
}

VDV_ORG_ID_LOGO = {
    35: "pass/logo-hvv.png",
    36: "pass/logo-rmv.png",
    57: "pass/logo-dsw.png",
    70: "pass/logo-vrr.png",
    77: "pass/logo-wt.png",
    102: "pass/logo-vrs.png",
    103: "pass/logo-swb.png",
    6212: "pass/logo-vrs.png",
    6234: "pass/logo-vvs.png",
    6310: "pass/logo-svv.png",
    6441: "pass/logo-kvg.png",
    6496: "pass/logo-naldo.png",
    6613: "pass/logo-arriva.png",
}

RSP_ORG_LOGO = {
    "TT": "pass/logo-tt.png",
    "CS": "pass/logo-cs.png",
    "RE": "pass/logo-re.png",
}
