"""Celery application configuration."""

from celery import Celery

from .config import settings

# Create Celery app
celery_app = Celery(
    "url_to_llm",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.crawler_tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minute soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-old-jobs": {
        "task": "app.tasks.crawler_tasks.cleanup_old_jobs",
        "schedule": 86400.0,  # Daily
    },
}