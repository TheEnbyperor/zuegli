from . import models, eos, apn

def update_all():
    for oauth in models.AccountOAuth.objects.filter(provider="sbahn_berlin", device_id__isnull=False):
        update_sbahn_berlin_tickets(oauth.account)

        for t in oauth.tickets.all():
            apn.notify_ticket_if_renewed(t)

def update_sbahn_berlin_tickets(account: "models.Account"):
    eos.update_eos_tickets(account, "sbahn_berlin", "https://sbahn-ber.tickeos.de", "sbb")
