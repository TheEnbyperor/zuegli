import json
import base64
import binascii
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .. import ticket, aztec


@csrf_exempt
def upload_aztec(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    if request.content_type != 'application/json':
        return HttpResponse(status=400)

    try:
        data = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)

    if "barcode_data" not in data:
        return HttpResponse(status=400)

    try:
        barcode_data = base64.b64decode(data["barcode_data"])
    except binascii.Error:
        return HttpResponse(status=400)

    try:
        ticket_obj = ticket.update_from_subscription_barcode(barcode_data, account=None)
    except ticket.TicketError as e:
        return HttpResponse(json.dumps({
            "title": e.title,
            "message": e.message,
            "exception": e.exception,
        }), status=422, content_type="application/json")

    return HttpResponse(json.dumps({
        "ticket_id": ticket_obj.id,
        "access_token": ticket_obj.pkpass_authentication_token
    }), content_type="application/json")


@csrf_exempt
def upload_aztec_img(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    if request.content_type != 'multipart/form-data':
        return HttpResponse(status=400)

    file = request.FILES["photo"]
    if file.size > 16 * 1024 * 1024:
        return HttpResponse(json.dumps({
            "title": "Too large",
            "message": "The photo must be less than 16MB"
        }), status=422, content_type="application/json")
    elif file.content_type not in ("image/jpeg", "image/png"):
        return HttpResponse(json.dumps({
            "title": "Unsupported",
            "message": "The photo must be a JPEG or PNG"
        }), status=422, content_type="application/json")

    scan_speed = request.POST.get("scan_speed", "slow")
    if scan_speed not in [ "slow", "normal", "fast" ]:
        return HttpResponse(json.dumps({
            "title": "Bad setting",
            "message": "Scan speed can only be one of 'slow', 'normal' or 'fast'"
        }), status=400, content_type="application/json")

    try:
        barcode_data = aztec.decode(file.read(), scan_speed=scan_speed)
    except aztec.AztecError as e:
        return HttpResponse(json.dumps({
            "title": "Unable to decode",
            "message": str(e)
        }), status=422, content_type="application/json")

    try:
        ticket_obj = ticket.update_from_subscription_barcode(barcode_data, account=None)
    except ticket.TicketError as e:
        return HttpResponse(json.dumps({
            "title": e.title,
            "message": e.message,
            "exception": e.exception,
        }), status=422, content_type="application/json")

    return HttpResponse(json.dumps({
        "ticket_id": ticket_obj.id,
        "access_token": ticket_obj.pkpass_authentication_token
    }), content_type="application/json")
