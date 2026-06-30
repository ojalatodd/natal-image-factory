from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.ai import suggest_project_name
from app.database import get_db
from app.deps import get_current_user
from app.models import Job, Project, ProjectStatus, User
from app import progress
from app.schemas import CostEstimateOut, DownloadOut, ProjectCreate, ProjectOut, ProjectSettings
from app.storage import delete_object, presigned_url
from app.tasks import run_pipeline

router = APIRouter(prefix="/projects", tags=["projects"])
limiter = Limiter(key_func=get_remote_address)

# Approximate OpenAI pricing per minute / per image (USD, as of 2025)
_WHISPER_PER_MIN = 0.006
_GPT4O_MINI_PER_1K_IN = 0.150 / 1000
_GPT4O_MINI_PER_1K_OUT = 0.600 / 1000
_GPT4O_VISION_PER_1K_IN = 2.50 / 1000
_GPT4O_VISION_PER_1K_OUT = 10.00 / 1000
_DALLE3_PER_IMAGE = 0.040


def _estimate_costs(project: Project) -> dict:
    """Estimate OpenAI API costs for a pipeline run based on project settings."""
    audio_min = (project.audio_duration_s or 0.0) / 60.0

    # Whisper: $0.006/min
    whisper_cost = audio_min * _WHISPER_PER_MIN

    # Estimate segment count from audio duration, or default for text-only
    est_segments = max(1, int(audio_min / 2.5)) if audio_min > 0 else 8

    # Segmentation: estimate input tokens from actual article text size
    article_chars = 0
    if project.source_text_key:
        try:
            from app.storage import download_bytes
            raw = download_bytes(project.source_text_key)
            article_chars = len(raw)
        except Exception:
            pass
    # Rough heuristic: ~4 chars per token for English text
    article_tokens = article_chars // 4
    transcript_tokens = int(audio_min * 150)  # ~150 words/min, ~1 token/word
    seg_in = min(article_tokens + transcript_tokens, 8000)
    seg_out = est_segments * 200  # ~200 tokens output per segment
    seg_cost = (
        seg_in * _GPT4O_MINI_PER_1K_IN + seg_out * _GPT4O_MINI_PER_1K_OUT
    )

    # Ranking: ~5 candidates per segment, ~500 tokens per image, ~50 tokens output
    rank_in = est_segments * 5 * 500
    rank_out = est_segments * 5 * 50
    rank_cost = (
        rank_in * _GPT4O_VISION_PER_1K_IN + rank_out * _GPT4O_VISION_PER_1K_OUT
    )

    # DALL-E fallback: only if enabled, estimate 1 image per project as worst case
    dalle_cost = _DALLE3_PER_IMAGE if project.ai_images_enabled else 0.0

    total = whisper_cost + seg_cost + rank_cost + dalle_cost

    return {
        "whisper_usd": round(whisper_cost, 4),
        "segmentation_usd": round(seg_cost, 4),
        "ranking_usd": round(rank_cost, 4),
        "dalle_fallback_usd": round(dalle_cost, 4),
        "total_usd": round(total, 4),
        "estimated_segments": est_segments,
        "audio_minutes": round(audio_min, 2),
    }


def _owned(db: Session, user: User, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/{project_id}/suggest-name")
def post_suggested_name(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Return a project name derived from the project's uploaded article text."""
    project = _owned(db, user, project_id)
    article_text = ""
    if project.source_text_key:
        try:
            from app.storage import download_bytes
            raw = download_bytes(project.source_text_key)
            article_text = raw.decode("utf-8", errors="replace")
        except Exception:
            pass
    return {"name": suggest_project_name(article_text)}


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = Project(user_id=user.id, name=body.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/duplicate", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def duplicate_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Duplicate a project's settings and source files (not segments/results)."""
    original = _owned(db, user, project_id)
    copy = Project(
        user_id=user.id,
        name=f"{original.name} (copy)",
        media_mix=original.media_mix,
        visual_style=original.visual_style,
        ai_images_enabled=original.ai_images_enabled,
        ai_video_motion=original.ai_video_motion,
        source_audio_key=original.source_audio_key,
        source_text_key=original.source_text_key,
        audio_duration_s=original.audio_duration_s,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


@router.patch("/{project_id}/rename", response_model=ProjectOut)
def rename_project(
    project_id: int,
    body: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Rename a project."""
    project = _owned(db, user, project_id)
    project.name = body.name
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page = max(1, page)
    per_page = min(100, max(1, per_page))
    return (
        db.query(Project)
        .filter(Project.user_id == user.id)
        .order_by(Project.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )


@router.get("/queue/status", response_model=list[ProjectOut])
def queue_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return projects currently in processing state for queue visibility."""
    return (
        db.query(Project)
        .filter(Project.user_id == user.id, Project.status == ProjectStatus.processing)
        .order_by(Project.updated_at.desc())
        .all()
    )


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _owned(db, user, project_id)


@router.get("/{project_id}/progress/latest")
def get_latest_progress(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Return the last known pipeline progress for a project (for restoring state after refresh)."""
    _owned(db, user, project_id)
    job = db.query(Job).filter(Job.project_id == project_id).order_by(Job.id.desc()).first()
    if not job:
        return {"stage": None, "progress_pct": 0, "message": None, "error": None}
    return {
        "stage": job.stage,
        "progress_pct": job.progress_pct,
        "message": job.message,
        "error": job.error,
    }


@router.patch("/{project_id}/settings", response_model=ProjectOut)
def update_settings(
    project_id: int,
    body: ProjectSettings,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _owned(db, user, project_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/generate", response_model=ProjectOut)
@limiter.limit("3/minute")
def generate(request: Request, project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _owned(db, user, project_id)
    if not project.source_audio_key and not project.source_text_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload an article text or voiceover first")
    if project.status == ProjectStatus.processing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pipeline already running")
    project.status = ProjectStatus.processing
    db.commit()
    db.refresh(project)
    task = run_pipeline.delay(project.id)
    # Store the Celery task ID so we can cancel later
    job = db.query(Job).filter(Job.project_id == project.id).order_by(Job.id.desc()).first()
    if job is None:
        job = Job(project_id=project.id, stage="start", progress_pct=0)
        db.add(job)
    job.celery_task_id = task.id
    db.commit()
    return project


@router.post("/{project_id}/cancel", response_model=ProjectOut)
def cancel_pipeline(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Cancel a running pipeline."""
    project = _owned(db, user, project_id)
    if project.status != ProjectStatus.processing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pipeline is not running")
    job = db.query(Job).filter(Job.project_id == project.id).order_by(Job.id.desc()).first()
    if job and job.celery_task_id:
        from app.celery_app import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True)
    project.status = ProjectStatus.draft
    db.commit()
    db.refresh(project)
    progress.publish(project_id, "cancelled", 0, "Pipeline cancelled by user")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _owned(db, user, project_id)
    if project.status == ProjectStatus.processing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete a project while processing")
    # Clean up Spaces objects
    for key_attr in ("source_audio_key", "source_text_key"):
        key = getattr(project, key_attr)
        if key:
            try:
                delete_object(key)
            except Exception:
                pass
    try:
        delete_object(f"output/project_{project.id}.zip")
    except Exception:
        pass
    db.delete(project)
    db.commit()


@router.get("/{project_id}/cost-estimate", response_model=CostEstimateOut)
def cost_estimate(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _owned(db, user, project_id)
    if not project.source_audio_key and not project.source_text_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload text or audio first")
    return _estimate_costs(project)


@router.get("/{project_id}/download", response_model=DownloadOut)
def download(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _owned(db, user, project_id)
    if project.status not in (ProjectStatus.complete, ProjectStatus.review):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package not ready")
    import re
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', project.name).strip().rstrip(".") or f"project_{project.id}"
    return DownloadOut(url=presigned_url(f"output/project_{project.id}.zip", filename=f"{safe_name}.zip"))
