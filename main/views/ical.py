from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .. import cal, models


def download_ics(request, pk):
    ticket_obj = get_object_or_404(models.Ticket, id=pk)
    cal_resp = cal.make_calendar(ticket_obj)

    response = HttpResponse()
    response["Content-Type"] = "text/calendar; charset=utf-8"
    response["Content-Disposition"] = f'attachment; filename="{ticket_obj.public_id()}.ics"'
    response.write(cal_resp)
    return response
