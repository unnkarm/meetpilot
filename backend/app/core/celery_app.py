from app.core.config import settings
from app.core.app_config import APP_CONFIG

try:
    from celery import Celery
    celery_app = Celery(
        "meetpilot",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.workers.meeting_processor", "app.workers.meeting_bot", "app.workers.vexa_meeting"],
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
    # Local ASR and model inference can take a while; avoid worker lockups.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_concurrency=APP_CONFIG.worker_concurrency,
    task_routes={"run_native_meeting_bot": {"queue": "meeting_bot"}, "run_vexa_meeting_bot": {"queue": "meeting_bot"}},
)


