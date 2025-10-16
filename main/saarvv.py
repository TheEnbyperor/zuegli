from celery import shared_task
from . import models, eos, apn

@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_all():
    for oauth in models.AccountOAuth.objects.filter(provider="saarvv", device_id__isnull=False):
        update_saarvv_tickets.delay(oauth.account_id)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=3, default_retry_delay=3,
    ignore_result=True
)
def update_saarvv_tickets(account_id):
    account = models.Account.objects.get(pk=account_id)
    eos.update_eos_tickets(account, "saarvv")