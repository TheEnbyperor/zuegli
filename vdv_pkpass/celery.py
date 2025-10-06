import os
import celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vdv_pkpass.settings')

app = celery.Celery('vdv_pkpass')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.task_routes = {
    "main.db_abo.update_abo_tickets": { "queue": "bg" },
    "main.db_bc.update_account": { "queue": "bg" },
    "main.db_ticket.update_account": { "queue": "bg" },
    "main.sbahn_berlin.update_sbahn_berlin_tickets": { "queue": "bg" },
    "main.hvv.update_hvv_tickets": { "queue": "bg" },
    "main.mvv.update_mvv_tickets": { "queue": "bg" },
    "main.raileasy.update_tickets": { "queue": "bg" },
    "main.saarvv.update_saarvv_tickets": { "queue": "bg" },
}