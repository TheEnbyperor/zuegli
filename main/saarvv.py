from . import models, eos, apn


def update_all():
    for account in models.Account.objects.filter(saarvv_device_id__isnull=False):
        eos.update_eos_tickets(account, "saarvv", "https://saarvv.tickeos.de", "saarvv")

        for t in account.saarvv_tickets.all():
            apn.notify_ticket_if_renewed(t)
