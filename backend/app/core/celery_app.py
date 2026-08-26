from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "document_intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Celery configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
)

# Auto-discover tasks from packages
celery_app.autodiscover_tasks(["app"])
