from . import models, eos, apn


def update_all():
    for oauth in models.AccountOAuth.objects.filter(provider="saarvv", device_id__isnull=False):
        update_saarvv_tickets(oauth.account)

        for t in oauth.tickets.all():
            apn.notify_ticket_if_renewed(t)

def update_saarvv_tickets(account: "models.Account"):
    eos.update_eos_tickets(account, "saarvv", "https://saarvv.tickeos.de", "saarvv")