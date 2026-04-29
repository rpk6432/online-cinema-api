from celery import Celery
from celery.schedules import crontab

from core.config import settings

app = Celery("online_cinema")

app.config_from_object(
    {
        "broker_url": settings.redis_url,
        "result_backend": None,
        "task_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "enable_utc": True,
        "task_soft_time_limit": 120,
        "task_time_limit": 180,
        "worker_prefetch_multiplier": 1,
        "imports": ["tasks.email", "tasks.cleanup"],
        "beat_schedule": {
            "cleanup-expired-tokens": {
                "task": "tasks.cleanup.cleanup_expired_tokens",
                "schedule": crontab(hour="*/6"),
            },
        },
    }
)
