"""Pipeline progress tracking: persisted to DB and published to Redis pub/sub
so the API can stream live updates to the SPA over WebSocket.
"""
from __future__ import annotations

import json

import redis

from app.config import settings
from app.database import SessionLocal
from app.models import Job, Project, ProjectStatus

_redis = redis.Redis.from_url(settings.redis_url)


def channel(project_id: int) -> str:
    return f"progress:{project_id}"


def publish(project_id: int, stage: str, pct: int, message: str | None = None, error: str | None = None) -> None:
    """Upsert the Job row and publish a progress event."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.project_id == project_id).order_by(Job.id.desc()).first()
        if job is None:
            job = Job(project_id=project_id)
            db.add(job)
        job.stage = stage
        job.progress_pct = pct
        job.message = message
        job.error = error
        db.commit()
    finally:
        db.close()

    payload = json.dumps({"stage": stage, "progress_pct": pct, "message": message, "error": error})
    _redis.publish(channel(project_id), payload)


def set_project_status(project_id: int, status: ProjectStatus) -> None:
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if project:
            project.status = status
            db.commit()
    finally:
        db.close()
