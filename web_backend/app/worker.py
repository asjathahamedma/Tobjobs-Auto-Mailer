from celery import Celery

from web_backend.app.settings import get_settings

settings = get_settings()
celery_app = Celery("topjobs", broker=settings.redis_url)
celery_app.conf.update(
    accept_content=["json"],
    task_ignore_result=True,
    task_serializer="json",
    result_serializer="json",
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
)
