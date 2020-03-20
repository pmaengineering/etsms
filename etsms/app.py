from celery import Celery
from celery.schedules import crontab

import config.settings as settings


app = Celery(
    broker=settings.REDIS_URL, 
    backend=settings.REDIS_URL,
    include=[
        'etsms.tasks.sms',
    ],
)

# Addis Ababa is UTC+3
app.conf.timezone = 'UTC'
app.conf.beat_schedule = {
    'send-to-et': {
        'task': 'etsms.tasks.sms.send_all_sms_for_today',
        'schedule': crontab(minute=0, hour=6),
    },
}