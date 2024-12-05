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
from . import models, rsp, templatetags, vdv

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
                    if (
                            "fromStationNum" in document or
                            "fromStationNameUTF8" in document or
                            "fromStationNameIA5" in document
                    ) and (
                            "toStationNum" in document or
                            "toStationNameUTF8" in document or
                            "toStationNameIA5" in document
                    ):
                        return "transit", settings.GWALLET_CONF["train_ticket_pass_class"]
                    else:
                        return "generic", settings.GWALLET_CONF["train_pass_class"]
                elif document_type == "customerCard":
                    return "generic", settings.GWALLET_CONF["bahncard_pass_class"]
    elif isinstance(ticket_instance, models.VDVTicketInstance):
        return "generic", settings.GWALLET_CONF["train_pass_class"]
    elif isinstance(ticket_instance, models.RSPTicketInstance):
        ticket_data = ticket_instance.as_ticket()
        if isinstance(ticket_data.data, rsp.RailcardData):
            return "generic", settings.GWALLET_CONF["railcard_pass_class"]

    return None


def ticket_class_name(class_code: str):
    class_name = {
        "defaultValue": {
            "language": "en",
            "value": class_code,
        }
    }
    if class_code == "first":
        class_name = {
            "translatedValues": [{
                "language": "de",
                "value": "1."
            }, {
                "language": "nl",
                "value": "1e"
            }, {
                "language": "cy",
                "value": "1af"
            }],
            "defaultValue": {
                "language": "en-gb",
                "value": "First"
            }
        }
    elif class_code == "second":
        class_name = {
            "translatedValues": [{
                "language": "de",
                "value": "2."
            }, {
                "language": "nl",
                "value": "2e"
            }, {
                "language": "nl",
                "value": "2ail"
            }],
            "defaultValue": {
                "language": "en-gb",
                "value": "Second"
            }
        }
    return class_name


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
        "imageModulesData": [],
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

    if ticket.ticket_type == ticket.TYPE_DEUTCHLANDTICKET:
        obj["imageModulesData"].append({
            "id": "thumb",
            "mainImage": {
                "sourceUri": {
                    "uri": urllib.parse.urljoin(
                        settings.EXTERNAL_URL_BASE,
                        static("pass/logo-dt@3x.png"),
                    )
                }
            }
        })

    ticket_instance = ticket.active_instance()
    if isinstance(ticket_instance, models.UICTicketInstance):
        ticket_type = None
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
                    ticket_type = "generic"
                    obj["classId"] = f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['train_pass_class']}"
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

                    from_station = templatetags.rics.get_station(document["fromStationNum"],
                                                                 document) if "fromStationNum" in document else None
                    to_station = templatetags.rics.get_station(document["toStationNum"],
                                                               document) if "toStationNum" in document else None

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

                    if "originName" in obj["ticketLegs"][0] and "destinationName" in obj["ticketLegs"][0]:
                        ticket_type = "transit"
                        obj[
                            "classId"] = f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['train_ticket_pass_class']}"
                        obj["tripType"] = "ROUND_TRIP" if document["returnIncluded"] else "ONE_WAY"
                        if distributor := ticket_data.distributor():
                            obj["ticketLegs"][0]["transitOperatorName"] = {
                                "defaultValue": {
                                    "language": "en",
                                    "value": distributor["full_name"],
                                }
                            }
                    else:
                        if distributor := ticket_data.distributor():
                            obj["textModulesData"].append({
                                "id": "distributor",
                                "localizedHeader": {
                                    "translatedValues": [{
                                        "language": "de",
                                        "value": "Ausstellende Organisation"
                                    }, {
                                        "language": "nl",
                                        "value": "Uitgevende Organisatie"
                                    }, {
                                        "language": "cy",
                                        "value": "Cwni dyddori"
                                    }],
                                    "defaultValue": {
                                        "language": "en-gb",
                                        "value": "Issuing Organisation"
                                    }
                                },
                                "body": distributor["full_name"],
                            })

                    if "classCode" in document:
                        if ticket_type == "transit":
                            if document["classCode"] == "first":
                                obj["ticketLegs"][0]["ticketSeat"]["fareClass"] = "FIRST"
                            elif document["classCode"] == "second":
                                obj["ticketLegs"][0]["ticketSeat"]["fareClass"] = "ECONOMY"
                        else:
                            obj["textModulesData"].append({
                                "id": "class",
                                "localizedHeader": {
                                    "translatedValues": [{
                                        "language": "de",
                                        "value": "Klasse"
                                    }, {
                                        "language": "nl",
                                        "value": "Klasse"
                                    }, {
                                        "language": "cy",
                                        "value": "Dosbarth"
                                    }],
                                    "defaultValue": {
                                        "language": "en-gb",
                                        "value": "Class"
                                    }
                                },
                                "localizedBody": ticket_class_name(document["classCode"])
                            })

                    if len(document.get("tariffs")) >= 1:
                        tariff = document["tariffs"][0]
                        if "tariffDesc" in tariff:
                            if ticket_type == "transit":
                                obj["ticketLegs"][0]["fareName"] = {
                                    "defaultValue": {
                                        "language": "en",
                                        "value": tariff["tariffDesc"]
                                    }
                                }
                            else:
                                obj["header"] = {
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
                                    }, {
                                        "language": "nl",
                                        "value": "Kortingskaart"
                                    }, {
                                        "language": "cy",
                                        "value": "Cerdyn gostwng"
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
                        train_number = train_link.get("trainIA5") or str(train_link.get("trainNum"))
                        obj["ticketLegs"][0]["departureDateTime"] = departure_time.isoformat()
                        obj["ticketLegs"][0]["carriage"] = train_number

                    if "productIdIA5" in document:
                        if "header" in obj or ticket_type == "transit":
                            obj["textModulesData"].append({
                                "id": "product-id",
                                "localizedHeader": {
                                    "translatedValues": [{
                                        "language": "de",
                                        "value": "Produkt"
                                    }, {
                                        "language": "nl",
                                        "value": "Product"
                                    }, {
                                        "language": "de",
                                        "value": "Cynnyrch"
                                    }],
                                    "defaultValue": {
                                        "language": "en-gb",
                                        "value": "Product"
                                    }
                                },
                                "body": document["productIdIA5"],
                            })
                        else:
                            obj["header"] = {
                                "defaultValue": {
                                    "language": "en",
                                    "value": document["productIdIA5"],
                                }
                            }

                    if "validRegionDesc" in document:
                        obj["textModulesData"].append({
                            "id": "valid-region",
                            "localizedHeader": {
                                "translatedValues": [{
                                    "language": "de",
                                    "value": "Gültigkeit"
                                }, {
                                    "language": "nl",
                                    "value": "Geldigheid"
                                }, {
                                    "language": "cy",
                                    "value": "Dilysrwydd"
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
                                    }, {
                                        "language": "nl",
                                        "value": "Retour geldigheid"
                                    }, {
                                        "language": "cy",
                                        "value": "Dilysrwydd dychweldaith"
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
                    obj[
                        "classId"] = f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['bahncard_pass_class']}"
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
                                }, {
                                    "language": "de",
                                    "value": "Kaart-ID"
                                }, {
                                    "language": "cy",
                                    "value": "Rhif cerdyn"
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
                                }, {
                                    "language": "de",
                                    "value": "Kaart-ID"
                                }, {
                                    "language": "cy",
                                    "value": "Rhif cerdyn"
                                }],
                                "defaultValue": {
                                    "language": "en-gb",
                                    "value": "Card ID"
                                }
                            },
                            "body": str(document["cardIdNum"]),
                        })

                    if "classCode" in document:
                        obj["textModulesData"].append({
                            "id": "class",
                            "localizedHeader": {
                                "translatedValues": [{
                                    "language": "de",
                                    "value": "Klasse"
                                }, {
                                    "language": "nl",
                                    "value": "Klasse"
                                }, {
                                    "language": "cy",
                                    "value": "Dosbarth"
                                }],
                                "defaultValue": {
                                    "language": "en-gb",
                                    "value": "Class"
                                }
                            },
                            "localizedBody": ticket_class_name(document["classCode"])
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
                            }, {
                                "language": "nl",
                                "value": "Geboortedatum"
                            }, {
                                "language": "de",
                                "value": "Dyddiad geni"
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
                            }, {
                                "language": "nl",
                                "value": "Paspoortnummer"
                            }, {
                                "language": "cy",
                                "value": "Rhif pasbort"
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
                                }, {
                                    "language": "nl",
                                    "value": "Reiziger"
                                }, {
                                    "language": "cy",
                                    "value": "Teithiwr"
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
                }, {
                    "language": "nl",
                    "value": "Uitgegeven om"
                }, {
                    "language": "cy",
                    "value": "Dyddorwyd am"
                }],
                "defaultValue": {
                    "language": "en-gb",
                    "value": "Issued at"
                }
            },
            "body": issued_at.strftime("%H:%M %d.%m.%Y"),
        })

        if ticket_type:
            return obj, ticket_type

    elif isinstance(ticket_instance, models.VDVTicketInstance):
        ticket_data = ticket_instance.as_ticket()

        validity_start = ticket_data.ticket.validity_start.as_datetime().astimezone(pytz.utc)
        validity_end = ticket_data.ticket.validity_end.as_datetime().astimezone(pytz.utc)
        issued_at = ticket_data.ticket.transaction_time.as_datetime().astimezone(pytz.utc)

        obj["logo"] = {
            "sourceUri": {
                "uri": urllib.parse.urljoin(
                    settings.EXTERNAL_URL_BASE,
                    static("pass/icon@3x.png"),
                )
            },
        }
        obj["hexBackgroundColor"] = "#ffffff"
        obj["classId"] = f"{settings.GWALLET_CONF['issuer_id']}.{settings.GWALLET_CONF['train_pass_class']}"
        obj["barcode"] = {
            "type": "AZTEC",
            "alternateText": str(ticket_data.ticket.ticket_id),
            "value": bytes(ticket_instance.barcode_data).decode("iso-8859-1"),
        }

        if ticket_data.ticket.product_org_id == 3000:
            obj["cardTitle"] = {
                "defaultValue": {
                    "language": "en",
                    "value": ticket_data.ticket.ticket_org_name()
                }
            }
        else:
            obj["cardTitle"] = {
                "defaultValue": {
                    "language": "en",
                    "value": ticket_data.ticket.product_org_name()
                }
            }

        obj["validTimeInterval"] = {
            "start": {
                "date": validity_start.isoformat()
            },
            "end": {
                "date": validity_end.isoformat()
            }
        }
        obj["header"] = {
            "defaultValue": {
                "language": "en",
                "value": ticket_data.ticket.product_name()
            }
        }
        obj["textModulesData"].append({
            "id": "product-org",
            "localizedHeader": {
                "translatedValues": [{
                    "language": "de",
                    "value": "Produktorganisation"
                }, {
                    "language": "nl",
                    "value": "Productorganisatie"
                }, {
                    "language": "cy",
                    "value": "Cynnyrchgwni"
                }],
                "defaultValue": {
                    "language": "en-gb",
                    "value": "Product Organisation"
                }
            },
            "body": ticket_data.ticket.product_org_name()
        })
        obj["textModulesData"].append({
            "id": "ticket-id",
            "localizedHeader": {
                "translatedValues": [{
                    "language": "de",
                    "value": "Ticket-ID"
                }, {
                    "language": "nl",
                    "value": "Ticket-ID"
                }, {
                    "language": "cy",
                    "value": "Rhif tocyn"
                }],
                "defaultValue": {
                    "language": "en-gb",
                    "value": "Ticket ID"
                }
            },
            "body": str(ticket_data.ticket.ticket_id)
        })
        obj["textModulesData"].append({
            "id": "ticket-org",
            "localizedHeader": {
                "translatedValues": [{
                    "language": "de",
                    "value": "Ticketverkaufsorganisation"
                }, {
                    "language": "nl",
                    "value": "Ticketorganisatie"
                }, {
                    "language": "cy",
                    "value": "Cwni tocynnu"
                }],
                "defaultValue": {
                    "language": "en-gb",
                    "value": "Ticketing Organisation"
                }
            },
            "body": ticket_data.ticket.ticket_org_name()
        })
        obj["textModulesData"].append({
            "id": "issued-at",
            "localizedHeader": {
                "translatedValues": [{
                    "language": "de",
                    "value": "Ausgestellt am"
                }, {
                    "language": "nl",
                    "value": "Uitgegeven om"
                }, {
                    "language": "cy",
                    "value": "Dyddorwyd am"
                }],
                "defaultValue": {
                    "language": "en-gb",
                    "value": "Issued at"
                }
            },
            "body": issued_at.strftime("%H:%M %d.%m.%Y"),
        })
        obj["textModulesData"].append({
            "id": "issuing-org",
            "localizedHeader": {
                "translatedValues": [{
                    "language": "de",
                    "value": "Ausstellende Organisation"
                }, {
                    "language": "nl",
                    "value": "Uitgevende Organisatie"
                }, {
                    "language": "cy",
                    "value": "Cwni dyddori"
                }],
                "defaultValue": {
                    "language": "en-gb",
                    "value": "Issuing Organisation"
                }
            },
            "body": ticket_data.ticket.kvp_org_name()
        })

        for elm in ticket_data.ticket.product_data:
            if isinstance(elm, vdv.ticket.PassengerData):
                obj["textModulesData"].append({
                    "id": "traveler",
                    "localizedHeader": {
                        "translatedValues": [{
                            "language": "de",
                            "value": "Fahrgast"
                        }, {
                            "language": "nl",
                            "value": "Reiziger"
                        }, {
                            "language": "cy",
                            "value": "Teithiwr"
                        }],
                        "defaultValue": {
                            "language": "en-gb",
                            "value": "Traveler"
                        }
                    },
                    "body": f"{elm.forename} {elm.surname}",
                })
                if elm.date_of_birth:
                    obj["textModulesData"].append({
                        "id": "dob",
                        "localizedHeader": {
                            "translatedValues": [{
                                "language": "de",
                                "value": "Geburtsdatum"
                            }, {
                                "language": "nl",
                                "value": "Geboortedatum"
                            }, {
                                "language": "cy",
                                "value": "Dyddiad geni"
                            }],
                            "defaultValue": {
                                "language": "en-gb",
                                "value": "Date of Birth"
                            }
                        },
                        "body": elm.date_of_birth.as_date().strftime("%d.%m.%Y"),
                    })

        return obj, "generic"

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
            obj["imageModulesData"].append({
                "id": "photo",
                "mainImage": {
                    "sourceUri": {
                        "uri": f"{settings.EXTERNAL_URL_BASE}{photo_url}",
                    }
                }
            })
            obj["textModulesData"].append({
                "id": "traveler-1",
                "localizedHeader": {
                    "translatedValues": [{
                        "language": "de",
                        "value": "Fahrgast"
                    }, {
                        "language": "nl",
                        "value": "Reiziger"
                    }, {
                        "language": "cy",
                        "value": "Teithiwr"
                    }],
                    "defaultValue": {
                        "language": "en-gb",
                        "value": "Traveler"
                    }
                },
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
                "localizedHeader": {
                    "translatedValues": [{
                        "language": "de",
                        "value": "Ausstellende Organisation"
                    }, {
                        "language": "nl",
                        "value": "Uitgevende Organisatie"
                    }, {
                        "language": "cy",
                        "value": "Cwni dyddori"
                    }],
                    "defaultValue": {
                        "language": "en-gb",
                        "value": "Issuing Organisation"
                    }
                },
                "body": ticket_data.data.issuer_name()
            })
            obj["textModulesData"].append({
                "id": "railcard-number",
                "localizedHeader": {
                    "translatedValues": [{
                        "language": "de",
                        "value": "Railcard-Nummer"
                    }, {
                        "language": "nl",
                        "value": "Railcard-nummer"
                    }, {
                        "language": "cy",
                        "value": "Rhif Railcard"
                    }],
                    "defaultValue": {
                        "language": "en-gb",
                        "value": "Railcard number",
                    }
                },
                "body": ticket_data.data.railcard_number
            })
            if ticket_data.data.free_use:
                obj["textModulesData"].append({
                    "id": "notes",
                    "localizedHeader": {
                        "translatedValues": [{
                            "language": "de",
                            "value": "Notiz"
                        }, {
                            "language": "nl",
                            "value": "Opmerking"
                        }, {
                            "language": "cy",
                            "value": "Nodyn"
                        }],
                        "defaultValue": {
                            "language": "en-gb",
                            "value": "Notes",
                        }
                    },
                    "body": ticket_data.data.free_use
                })

            return obj, "generic"

    return obj, None
