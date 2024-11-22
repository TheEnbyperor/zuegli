import typing
import googleapiclient.discovery
import googleapiclient.errors
import google.auth.crypt
import google.auth.jwt
import urllib.parse
from django.conf import settings
from django.templatetags.static import static
from django.shortcuts import reverse
from . import models, rsp

client = googleapiclient.discovery.build("walletobjects", "v1", credentials=settings.GOOGLE_CREDS)

def sync_ticket(ticket: "models.Ticket"):
    object_id = f"{settings.GWALLET_CONF['issuer_id']}.{ticket.pk.replace('=', '')}"
    data, obj_type = make_ticket_obj(ticket, object_id)
    try:
        if obj_type == "generic":
            client.genericobject().get(resourceId=object_id).execute()
    except googleapiclient.errors.HttpError as e:
        if e.status_code != 404:
            raise e
        else:
            if obj_type == "generic":
                client.genericobject().insert(body=data).execute()
    else:
        if obj_type == "generic":
            client.genericobject().update(resourceId=object_id, body=data).execute()

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
    if isinstance(ticket_instance, models.RSPTicketInstance):
        ticket_data = ticket_instance.as_ticket()
        if isinstance(ticket_data.data, rsp.RailcardData):
            return "generic", settings.GWALLET_CONF["railcard_pass_class"]

    return None

def make_ticket_obj(ticket: "models.Ticket", object_id: str) -> typing.Tuple[dict, typing.Optional[str]]:
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
        }
    }

    ticket_instance = ticket.active_instance()
    if isinstance(ticket_instance, models.RSPTicketInstance):
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
            obj["textModulesData"] = [{
                "id": "traveler-1",
                "header": "Issued to",
                "body": ticket_data.data.passenger_1_name(),
            }]
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