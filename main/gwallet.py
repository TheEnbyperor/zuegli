import typing
import googleapiclient.discovery
import googleapiclient.errors
import google.auth.crypt
import google.auth.jwt
import urllib.parse
import pytz
from django.conf import settings
from django.templatetags.static import static
from django.shortcuts import reverse
from . import models, rsp, templatetags

client = googleapiclient.discovery.build("walletobjects", "v1", credentials=settings.GOOGLE_CREDS)

def sync_ticket(ticket: "models.Ticket"):
    object_id = f"{settings.GWALLET_CONF['issuer_id']}.{ticket.pk.replace('=', '')}"
    data, obj_type = make_ticket_obj(ticket, object_id)
    try:
        if obj_type == "generic":
            client.genericobject().get(resourceId=object_id).execute()
        elif obj_type == "transit":
            client.transitobject().get(resourceId=object_id).execute()
    except googleapiclient.errors.HttpError as e:
        if e.status_code != 404:
            raise e
        else:
            if obj_type == "generic":
                client.genericobject().insert(body=data).execute()
            elif obj_type == "transit":
                client.transitobject().insert(body=data).execute()
    else:
        if obj_type == "generic":
            client.genericobject().update(resourceId=object_id, body=data).execute()
        elif obj_type == "transit":
            client.transitobject().update(resourceId=object_id, body=data).execute()

def create_jwt_link(ticket: "models.Ticket") -> typing.Optional[str]:
    object_id = f"{settings.GWALLET_CONF['issuer_id']}.{ticket.pk.replace('=', '')}"
    if d := ticket_class(ticket):
        obj_type, obj_class = d
    else:
        return None
    claims = {
        "iss": settings.GOOGLE_CREDS.service_account_email,
        "aud": "google",
        "origins": settings.ALLOWED_HOSTS,
        "typ": "savetowallet",
        "payload": {}
    }

    if obj_type == "generic":
        claims["payload"]["genericObjects"] = [{
            "id": object_id,
            "classId": obj_class,
        }]
    elif obj_type == "transit":
        claims["payload"]["transitObjects"] = [{
            "id": object_id,
            "classId": obj_class,
        }]

    token = google.auth.jwt.encode(settings.GOOGLE_SIGNER, claims).decode("utf-8")
    return f"https://pay.google.com/gp/v/save/{token}"

def ticket_class(ticket: "models.Ticket") -> typing.Optional[typing.Tuple[str, str]]:
    ticket_instance = ticket.active_instance()
    if isinstance(ticket_instance, models.UICTicketInstance):
        ticket_data = ticket_instance.as_ticket()
        if ticket_data.flex:
            if len(ticket_data.flex.data["transportDocument"]) >= 1:
                document_type, document = ticket_data.flex.data["transportDocument"][0]["ticket"]
                if document_type == "openTicket":
                    return "transit", settings.GWALLET_CONF["train_ticket_pass_class"]
                elif document_type == "customerCard":
                    return "generic", settings.GWALLET_CONF["bahncard_pass_class"]
    if isinstance(ticket_instance, models.RSPTicketInstance):
        ticket_data = ticket_instance.as_ticket()
        if isinstance(ticket_data.data, rsp.RailcardData):
            return "generic", settings.GWALLET_CONF["railcard_pass_class"]

    return None

def make_ticket_obj(ticket: "models.Ticket", object_id: str) -> typing.Tuple[dict, typing.Optional[str]]:
    from .views import passes

    ticket_url = reverse('ticket', kwargs={"pk": ticket.pk})

    obj = {
        "id": object_id,
        "state": "active",
        "passConstraints": {
            "screenshotEligibility": "INELIGIBLE",
            "nfcConstraint": [
                "BLOCK_PAYMENT",
                "BLOCK_CLOSED_LOOP_TRANSIT"
            ]
        },
        "appLinkData": {
            "webAppLinkInfo": {
                "appTarget": {
                    "targetUri": {
                        "uri": f"{settings.EXTERNAL_URL_BASE}{ticket_url}",
                        "description": "More info",
                        "id": "more-info"
                    }
                }
            }
        },
        "textModulesData": [],
        "linksModuleData": {
            "uris": []
        },
        "cardTitle": {
            "defaultValue": {
                "language": "de",
                "value": "BahnCard"
            }
        }
    }

    ticket_instance = ticket.active_instance()
    if isinstance(ticket_instance, models.UICTicketInstance):
        ticket_type = "transit"
        ticket_data = ticket_instance.as_ticket()
        issued_at = ticket_data.issuing_time().astimezone(pytz.utc)

        obj["logo"] = {
            "sourceUri": {
                "uri": urllib.parse.urljoin(
                    settings.EXTERNAL_URL_BASE,
                    static("pass/icon@3x.png"),
                )
            },
        }
        obj["hexBackgroundColor"] = "#ffffff"
        obj["barcode"] = {
            "type": "AZTEC",
            "alternateText": ticket_data.ticket_id(),
            "value": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
        }

        if ticket_id := ticket_data.ticket_id():
            obj["ticketNumber"] = ticket_id

        if distributor := ticket_data.distributor():
            obj["cardTitle"]["defaultValue"]["value"] = distributor["full_name"]
            if distributor["url"]:
                obj["linksModuleData"]["uris"].append({
                    "id": "distributor",
                    "description": distributor["full_name"],
                    "uri": distributor["url"],
                })

        if ticket_data.flex:
            obj["state"] = "ACTIVE" if ticket_data.flex.data["issuingDetail"]["activated"] else "INACTIVE"

            if len(ticket_data.flex.data["transportDocument"]) >= 1:
                document_type, document = ticket_data.flex.data["transportDocument"][0]["ticket"]
                if document_type == "openTicket":
                    obj["classId"] = f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['train_ticket_pass_class']}"

                    validity_start = templatetags.rics.rics_valid_from(document, issued_at)
                    validity_end = templatetags.rics.rics_valid_until(document, issued_at)
                    obj["validTimeInterval"] = {
                        "start": {
                            "date": validity_start.isoformat()
                        },
                        "end": {
                            "date": validity_end.isoformat()
                        }
                    }

                    obj["ticketLegs"] = [{
                        "ticketSeat": {}
                    }]

                    from_station = templatetags.rics.get_station(document["fromStationNum"], document) if "fromStationNum" in document else None
                    to_station = templatetags.rics.get_station(document["toStationNum"], document) if "toStationNum" in document else None

                    if distributor := ticket_data.distributor():
                        obj["ticketLegs"][0]["transitOperatorName"] = {
                            "defaultValue": {
                                "language": "en",
                                "value": distributor["full_name"],
                            }
                        }

                    if from_station:
                        obj["ticketLegs"][0]["originName"] = {
                            "defaultValue": {
                                "language": "en",
                                "value": from_station["name"]
                            }
                        }
                    elif "fromStationNameUTF8" in document:
                        obj["ticketLegs"][0]["originName"] = {
                            "defaultValue": {
                                "language": "en",
                                "value": document["fromStationNameUTF8"]
                            }
                        }
                    elif "fromStationIA5" in document:
                        obj["ticketLegs"][0]["originName"] = {
                            "defaultValue": {
                                "language": "en",
                                "value": document["fromStationIA5"]
                            }
                        }

                    if to_station:
                        obj["ticketLegs"][0]["destinationName"] = {
                            "defaultValue": {
                                "language": "en",
                                "value": to_station["name"]
                            }
                        }
                    elif "toStationNameUTF8" in document:
                        obj["ticketLegs"][0]["destinationName"] = {
                            "defaultValue": {
                                "language": "en",
                                "value": document["toStationNameUTF8"]
                            }
                        }
                    elif "toStationIA5" in document:
                        obj["ticketLegs"][0]["destinationName"] = {
                            "defaultValue": {
                                "language": "en",
                                "value": document["toStationIA5"]
                            }
                        }

                    obj["tripType"] = "ROUND_TRIP" if document["returnIncluded"] else "ONE_WAY"

                    if "classCode" in document:
                        if document["classCode"] == "first":
                            obj["ticketLegs"][0]["ticketSeat"]["fareClass"] = "FIRST"
                        elif document["classCode"] == "second":
                            obj["ticketLegs"][0]["ticketSeat"]["fareClass"] = "ECONOMY"

                    if len(document.get("tariffs")) >= 1:
                        tariff = document["tariffs"][0]
                        if "tariffDesc" in tariff:
                            obj["ticketLegs"][0]["fareName"] = {
                                "defaultValue": {
                                    "language": "en",
                                    "value": tariff["tariffDesc"]
                                }
                            }

                        for i, card in enumerate(tariff.get("reductionCard", [])):
                            obj["textModulesData"].append({
                                "id": f"reduction-card-{i}",
                                "localizedHeader": {
                                    "translatedValues": [{
                                        "language": "de",
                                        "value": "BahnCard"
                                    }],
                                    "defaultValue": {
                                        "language": "en-gb",
                                        "value": "Discount card"
                                    }
                                },
                                "body": card["cardName"]
                            })

                    if "validRegion" in document and document["validRegion"][0][0] == "trainLink":
                        train_link = document["validRegion"][0][1]
                        departure_time = templatetags.rics.rics_departure_time(train_link, issued_at)
                        train_number = train_link["trainIA5"] or str(train_link["trainNum"])
                        obj["ticketLegs"][0]["departureDateTime"] = departure_time.isoformat()
                        obj["ticketLegs"][0]["carriage"] = train_number

                    if "productIdIA5" in document:
                        obj["textModulesData"].append({
                            "id": "product-id",
                            "localizedHeader": {
                                "translatedValues": [{
                                    "language": "de",
                                    "value": "Produkt"
                                }],
                                "defaultValue": {
                                    "language": "en-gb",
                                    "value": "Product"
                                }
                            },
                            "body": document["productIdIA5"],
                        })

                    if "validRegionDesc" in document:
                        obj["textModulesData"].append({
                            "id": "valid-region",
                            "localizedHeader": {
                                "translatedValues": [{
                                    "language": "de",
                                    "value": "Gültigkeit"
                                }],
                                "defaultValue": {
                                    "language": "en-gb",
                                    "value": "Validity"
                                }
                            },
                            "body": document["validRegionDesc"],
                        })

                    if "returnDescription" in document:
                        return_document = document["returnDescription"]

                        if "validReturnRegionDesc" in return_document:
                            obj["textModulesData"].append({
                                "id": "valid-region",
                                "localizedHeader": {
                                    "translatedValues": [{
                                        "language": "de",
                                        "value": "Ruckfahrt gültigkeit"
                                    }],
                                    "defaultValue": {
                                        "language": "en-gb",
                                        "value": "Return validity"
                                    }
                                },
                                "body": return_document["validReturnRegionDesc"],
                            })

                elif document_type == "customerCard":
                    ticket_type = "generic"
                    obj["genericType"] = "GENERIC_LOYALTY_CARD"
                    obj["classId"] = f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['bahncard_pass_class']}"
                    obj["header"] = {
                        "defaultValue": {
                            "language": "en",
                            "value": ""
                        }
                    }

                    validity_start = templatetags.rics.rics_valid_from_date(document)
                    validity_end = templatetags.rics.rics_valid_until_date(document)
                    obj["validTimeInterval"] = {
                        "start": {
                            "date": validity_start.isoformat()
                        },
                        "end": {
                            "date": validity_end.isoformat()
                        }
                    }

                    if "cardIdIA5" in document:
                        obj["textModulesData"].append({
                            "id": "card-id",
                            "localizedHeader": {
                                "translatedValues": [{
                                    "language": "de",
                                    "value": "Kartennummer"
                                }],
                                "defaultValue": {
                                    "language": "en-gb",
                                    "value": "Card ID"
                                }
                            },
                            "body": document["cardIdIA5"],
                        })
                    elif "cardIdNum" in document:
                        obj["textModulesData"].append({
                            "id": "card-id",
                            "localizedHeader": {
                                "translatedValues": [{
                                    "language": "de",
                                    "value": "Kartennummer"
                                }],
                                "defaultValue": {
                                    "language": "en-gb",
                                    "value": "Card ID"
                                }
                            },
                            "body": str(document["cardIdNum"]),
                        })

                    if "classCode" in document:
                        class_name = document["classCode"]
                        if class_name == "first":
                            class_name = "1."
                        elif class_name == "second":
                            class_name = "2."
                        obj["textModulesData"].append({
                            "id": "class",
                            "localizedHeader": {
                                "translatedValues": [{
                                    "language": "de",
                                    "value": "Klasse"
                                }],
                                "defaultValue": {
                                    "language": "en-gb",
                                    "value": "Class"
                                }
                            },
                            "body": class_name
                        })

                    if "cardTypeDescr" in document:
                        obj["header"]["defaultValue"]["value"] = document["cardTypeDescr"]

                        if document["cardTypeDescr"] in passes.BC_STRIP_IMG:
                            obj["heroImage"] = {
                                "sourceUri": {
                                    "uri": urllib.parse.urljoin(
                                        settings.EXTERNAL_URL_BASE,
                                        static(passes.BC_STRIP_IMG[document["cardTypeDescr"]])
                                    )
                                }
                            }

            travellers = ticket_data.flex.data.get("travelerDetail", {}).get("traveler", [])
            if len(travellers) == 1:
                obj["passengerType"] = "SINGLE_PASSENGER"
            elif len(travellers) > 1:
                obj["passengerType"] = "MULTIPLE_PASSENGER"

            passenger_names = []
            for i, traveller in enumerate(travellers):
                first_name = traveller.get('firstName', "").strip()
                last_name = traveller.get('lastName', "").strip()
                passenger_names.append(f"{first_name} {last_name}")

                dob = templatetags.rics.rics_traveler_dob(traveller)
                dob_text = None
                if dob:
                    dob_text = f"{dob.day:02d}.{dob.month:02d}.{dob.year:04d}"
                else:
                    dob_year = traveller.get("yearOfBirth", 0)
                    dob_month = traveller.get("monthOfBirth", 0)
                    if dob_year != 0 and dob_month != 0:
                        dob_text = f"{dob_month:02d}.{dob_year:04d}"
                    elif dob_year != 0:
                        dob_text = f"{dob_year:04d}"

                if dob_text:
                    obj["textModulesData"].append({
                        "id": f"dob-{i}",
                        "localizedHeader": {
                            "translatedValues": [{
                                "language": "de",
                                "value": "Geburtsdatum"
                            }],
                            "defaultValue": {
                                "language": "en-gb",
                                "value": "Date of birth"
                            }
                        },
                        "body": dob_text,
                    })

                if "passportId" in traveller:
                    obj["textModulesData"].append({
                        "id": f"dob-{i}",
                        "localizedHeader": {
                            "translatedValues": [{
                                "language": "de",
                                "value": "Reisepassnr."
                            }],
                            "defaultValue": {
                                "language": "en-gb",
                                "value": "Passport number"
                            }
                        },
                        "body": traveller["passportId"],
                    })

            if passenger_names:
                if ticket_type == "transit":
                    obj["passengerName"] = "; ".join(passenger_names)
                else:
                    for i, name in enumerate(passenger_names):
                        obj["textModulesData"].append({
                            "id": f"traveler-{i}",
                            "localizedHeader": {
                                "translatedValues": [{
                                    "language": "de",
                                    "value": "Fahrgast"
                                }],
                                "defaultValue": {
                                    "language": "en-gb",
                                    "value": "Traveler"
                                }
                            },
                            "body": name
                        })

        obj["textModulesData"].append({
            "id": "issued-at",
            "localizedHeader": {
                "translatedValues": [{
                    "language": "de",
                    "value": "Ausgestellt am"
                }],
                "defaultValue": {
                    "language": "en-gb",
                    "value": "Issued at"
                }
            },
            "body": issued_at.isoformat(),
        })

        return obj, ticket_type

    elif isinstance(ticket_instance, models.RSPTicketInstance):
        obj["cardTitle"] = {
            "defaultValue": {
                "language": "en-GB",
                "value": "National Rail"
            }
        }
        obj["logo"] = {
            "sourceUri": {
                "uri": urllib.parse.urljoin(settings.EXTERNAL_URL_BASE, static("main/logo-nr.png"))
            },
        }
        obj["barcode"] = {
            "type": "AZTEC",
            "alternateText": f"{ticket_instance.issuer_id}-{ticket_instance.reference}",
            "value": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
        }

        ticket_data = ticket_instance.as_ticket()
        if isinstance(ticket_data.data, rsp.RailcardData):
            obj["classId"] = f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['railcard_pass_class']}"
            obj["genericType"] = "GENERIC_SEASON_PASS"
            if colour := ticket_data.data.background_colour():
                obj["hexBackgroundColor"] = colour
            obj["header"] = {
                "defaultValue": {
                    "language": "en-GB",
                    "value": (
                        f"SPECIMEN - {ticket_data.data.railcard_type_name()}"
                        if ticket_data.data.non_revenue else
                        ticket_data.data.railcard_type_name()
                    )
                }
            }
            obj["validTimeInterval"] = {
                "start": {
                    "date": ticket_data.data.validity_start_time().isoformat()
                },
                "end": {
                    "date": ticket_data.data.validity_end_time().isoformat()
                }
            }
            obj["notifications"] = {
                "expiryNotification": {
                    "enableNotification": True
                }
            }
            photo_url = reverse("ticket_pass_photo_banner", kwargs={"pk": ticket.pk})
            obj["imageModulesData"] = [{
                "id": "photo",
                "mainImage": {
                    "sourceUri": {
                        "uri": f"{settings.EXTERNAL_URL_BASE}{photo_url}",
                    }
                }
            }]
            obj["textModulesData"].append({
                "id": "traveler-1",
                "header": "Issued to",
                "body": ticket_data.data.passenger_1_name(),
            })
            if ticket_data.data.has_passenger_2():
                obj["textModulesData"].append({
                    "id": "traveler-2",
                    "header": "Companion",
                    "body": ticket_data.data.passenger_2_name(),
                })
            obj["textModulesData"].append({
                "id": "issuer",
                "header": "Issued by",
                "body": ticket_data.data.issuer_name()
            })
            obj["textModulesData"].append({
                "id": "railcard-number",
                "header": "Railcard number",
                "body": ticket_data.data.railcard_number
            })
            if ticket_data.data.free_use:
                obj["textModulesData"].append({
                    "id": "notes",
                    "header": "Notes",
                    "body": ticket_data.data.free_use
                })

            return obj, "generic"

    return obj, None