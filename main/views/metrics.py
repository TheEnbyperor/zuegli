from django.http import HttpResponse
from django.db.models import Count

from .. import models, vdv, uic, rsp

def metrics(request):
    out = []

    for t in models.Ticket.objects.all().values('ticket_type').annotate(total=Count('ticket_type')):
        out.append(f'ticket_count{{type="{t["ticket_type"]}"}} {t["total"]}')

    newest_ticket = models.Ticket.objects.order_by('-last_updated').first()
    if newest_ticket:
        out.append(f'newest_ticket_timestamp {newest_ticket.last_updated.timestamp()}')

    vdv_count = models.VDVTicketInstance.objects.all().count()
    out.append(f'ticket_instance_count{{type="vdv"}} {vdv_count}')

    for o in models.VDVTicketInstance.objects.all().values('ticket_org_id').annotate(total=Count('ticket_org_id')):
        org_id = o["ticket_org_id"]
        org_name = vdv.ticket.map_org_id(org_id)
        out.append(f'ticket_vdv_issuer{{org_id="{org_id}", org_name="{org_name}"}} {o["total"]}')

    uic_count = models.UICTicketInstance.objects.all().count()
    out.append(f'ticket_instance_count{{type="uic"}} {uic_count}')

    for o in models.UICTicketInstance.objects.all().values('distributor_rics').annotate(total=Count('distributor_rics')):
        rics = o["distributor_rics"]
        org = uic.rics.get_rics(rics)
        org_name = org["full_name"] if org else "Unknown"
        out.append(f'ticket_uic_issuer{{rics="{rics}", name="{org_name}"}} {o["total"]}')

    ssb_count = models.SSBTicketInstance.objects.all().count()
    out.append(f'ticket_instance_count{{type="ssb"}} {ssb_count}')

    for o in models.SSBTicketInstance.objects.all().values('distributor_rics').annotate(total=Count('distributor_rics')):
        rics = o["distributor_rics"]
        org = uic.rics.get_rics(rics)
        org_name = org["full_name"] if org else "Unknown"
        out.append(f'ticket_ssb_issuer{{rics="{rics}", name="{org_name}"}} {o["total"]}')

    rsp_count = models.RSPTicketInstance.objects.all().count()
    out.append(f'ticket_instance_count{{type="rsp"}} {rsp_count}')

    rsp_06_count = models.RSPTicketInstance.objects.filter(ticket_type="06").count()
    out.append(f'ticket_rsp_count{{type="06"}} {rsp_06_count}')
    rsp_08_count = models.RSPTicketInstance.objects.filter(ticket_type="08").count()
    out.append(f'ticket_rsp_count{{type="08"}} {rsp_08_count}')

    for o in models.RSPTicketInstance.objects.all().values('issuer_id').annotate(total=Count('issuer_id')):
        issuer_id = o["issuer_id"]
        org_name = rsp.issuers.issuer_name(issuer_id)
        out.append(f'ticket_rsp_issuer{{id="{issuer_id}", name="{org_name}"}} {o["total"]}')

    sncf_count = models.SNCFTicketInstance.objects.all().count()
    out.append(f'ticket_instance_count{{type="sncf"}} {sncf_count}')

    elb_count = models.ELBTicketInstance.objects.all().count()
    out.append(f'ticket_instance_count{{type="elb"}} {sncf_count}')

    return HttpResponse("\n".join(out), content_type="text/plain;charset=UTF-8")
