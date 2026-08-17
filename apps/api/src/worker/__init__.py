"""Celery worker configuration."""

from celery import Celery
from src.config import get_settings

settings = get_settings()

celery_app = Celery(
    "researchos",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["src.worker.tasks"])
