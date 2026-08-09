from app.core.config import settings

try:
    from celery import Celery
    celery_app = Celery(
        "meetpilot",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.workers.meeting_processor"],
    )
except ImportError:
    from unittest.mock import MagicMock
    celery_app = MagicMock()

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Audio processing (Gemini calls) can take a while; avoid worker lockups.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


