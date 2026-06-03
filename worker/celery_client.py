from celery import Celery
from core.config import settings

CLOUDAMQP_URL = settings.CELERY_WORKER_BROKER_URL

client = Celery("worker", broker=CLOUDAMQP_URL)