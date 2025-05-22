import os
import celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vdv_pkpass.settings')

app = celery.Celery('vdv_pkpass')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()