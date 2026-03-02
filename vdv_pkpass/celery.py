import os
import celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vdv_pkpass.settings')

app = celery.Celery('vdv_pkpass')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.task_routes = {
    "main.vdv.tasks.sync_blocklist": { "queue": "bg" },
    "main.uic.tasks.download_data": { "queue": "bg" },
    "main.db_abo.update_all": { "queue": "bg" },
    "main.db_abo.update_abo_tickets": { "queue": "bg" },
    "main.db_bc.update_all": { "queue": "bg" },
    "main.db_bc.update_account": { "queue": "bg" },
    "main.db_ticket.update_all": { "queue": "bg" },
    "main.db_ticket.update_account": { "queue": "bg" },
    "main.bahnbonus_vouchers.update_all": { "queue": "bg" },
    "main.bahnbonus_vouchers.update_account": { "queue": "bg" },
    "main.sbahn_berlin.update_all": { "queue": "bg" },
    "main.sbahn_berlin.update_sbahn_berlin_tickets": { "queue": "bg" },
    "main.avv.update_all": { "queue": "bg" },
    "main.avv.update_avv_tickets": { "queue": "bg" },
    "main.hvv.update_all": { "queue": "bg" },
    "main.hvv.update_hvv_tickets": { "queue": "bg" },
    "main.mvv.update_all": { "queue": "bg" },
    "main.mvv.update_mvv_tickets": { "queue": "bg" },
    "main.raileasy.update_tickets": { "queue": "bg" },
    "main.saarvv.update_all": { "queue": "bg" },
    "main.saarvv.update_saarvv_tickets": { "queue": "bg" },
    "gtfs.tasks.process_gtfs": { "queue": "bg" },
    "gtfs.tasks.process_all_gtfs_rt": { "queue": "bg" },
    "gtfs.tasks.process_gtfs_rt": { "queue": "bg" },
}