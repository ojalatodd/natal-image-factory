from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Project, User
from app.schemas import ProjectOut
from app.storage import upload_bytes

router = APIRouter(prefix="/projects", tags=["uploads"])

MAX_AUDIO_BYTES = 500 * 1024 * 1024  # 500 MB
ALLOWED_AUDIO = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a", "audio/x-m4a"}


def _owned(db: Session, user: User, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/{project_id}/uploads/text", response_model=ProjectOut)
async def upload_text(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _owned(db, user, project_id)
    data = await file.read()
    key = f"uploads/{project_id}/article_{file.filename}"
    upload_bytes(key, data, content_type=file.content_type or "text/plain")
    project.source_text_key = key
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/uploads/audio", response_model=ProjectOut)
async def upload_audio(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _owned(db, user, project_id)
    data = await file.read()
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio too large")
    key = f"uploads/{project_id}/voiceover_{file.filename}"
    upload_bytes(key, data, content_type=file.content_type or "audio/mpeg")
    project.source_audio_key = key
    db.commit()
    db.refresh(project)
    return project
