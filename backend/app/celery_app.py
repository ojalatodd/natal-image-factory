from celery import Celery

from app.config import settings

celery_app = Celery(
    "natal",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_max_tasks_per_child=20,        # recycle workers to release ffmpeg memory
    worker_concurrency=2,                  # guardrail for a 2 GiB Droplet
    task_acks_late=True,
)
