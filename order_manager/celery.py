import os
from celery import Celery
from celery.schedules import crontab

from order_manager import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'order_manager.settings')

app = Celery("order_manager")

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.beat_schedule = {
    'check-file-every-1-minute': {
        'task': 'orders.utils.refresh_data',
        'schedule': crontab(minute='*/1'),

    },
}
app.conf.timezone = 'UTC'
