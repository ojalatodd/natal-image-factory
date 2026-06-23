"""Celery task that runs the full pipeline for a project."""
from __future__ import annotations

from app import progress
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Project, ProjectStatus
from app.pipeline import stages


@celery_app.task(name="run_pipeline")
def run_pipeline(project_id: int) -> dict:
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        if project is None:
            return {"ok": False, "error": "project not found"}

        progress.set_project_status(project_id, ProjectStatus.processing)
        progress.publish(project_id, "start", 0, "Starting…")

        transcript = stages.transcribe(db, project)
        segments = stages.segment(db, project, transcript)
        stages.search_media(db, project, segments)
        stages.rank_match(db, project, segments)
        stages.acquire_process(db, project, segments)
        zip_key = stages.package(db, project, segments)

        progress.publish(project_id, "done", 100, "Ready for review")
        progress.set_project_status(project_id, ProjectStatus.review)
        return {"ok": True, "segments": len(segments), "zip_key": zip_key}
    except Exception as exc:  # noqa: BLE001 — surface any stage failure to the UI
        progress.publish(project_id, "error", 0, "Processing failed", error=str(exc))
        progress.set_project_status(project_id, ProjectStatus.error)
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()
