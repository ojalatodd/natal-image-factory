from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Project, ProjectStatus, User
from app.schemas import CostEstimateOut, DownloadOut, ProjectCreate, ProjectOut, ProjectSettings
from app.storage import delete_object, presigned_url
from app.tasks import run_pipeline

router = APIRouter(prefix="/projects", tags=["projects"])

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

    # Segmentation: ~2K input tokens (article + transcript), ~1K output
    seg_in = 2000
    seg_out = 1000
    seg_cost = (
        seg_in * _GPT4O_MINI_PER_1K_IN + seg_out * _GPT4O_MINI_PER_1K_OUT
    )

    # Ranking: ~5 candidates per segment, ~500 tokens per image, ~50 tokens output
    est_segments = max(1, int(audio_min / 2.5))
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


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = Project(user_id=user.id, name=body.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc()).all()


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
def generate(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _owned(db, user, project_id)
    if not project.source_audio_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a voiceover first")
    if not project.source_text_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload an article text first")
    if project.status == ProjectStatus.processing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pipeline already running")
    project.status = ProjectStatus.processing
    db.commit()
    db.refresh(project)
    run_pipeline.delay(project.id)
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
    if not project.source_audio_key or not project.source_text_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload text and audio first")
    return _estimate_costs(project)


@router.get("/{project_id}/download", response_model=DownloadOut)
def download(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _owned(db, user, project_id)
    if project.status not in (ProjectStatus.complete, ProjectStatus.review):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package not ready")
    return DownloadOut(url=presigned_url(f"output/project_{project.id}.zip"))
