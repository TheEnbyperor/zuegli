from . import models, eos, apn

def update_all():
    for account in models.Account.objects.filter(sbahn_berlin_device_id__isnull=False):
        update_sbahn_berlin_tickets(account)

        for t in account.sbahn_berlin_tickets.all():
            apn.notify_ticket_if_renewed(t)

def update_sbahn_berlin_tickets(account: models.Account):
    eos.update_eos_tickets(account, "sbahn_berlin", "https://sbahn-ber.tickeos.de", "sbb")
