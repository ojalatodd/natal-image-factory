from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Project, User
from app.schemas import ProjectOut
from app.storage import upload_bytes

router = APIRouter(prefix="/projects", tags=["uploads"])
limiter = Limiter(key_func=get_remote_address)

MAX_AUDIO_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_TEXT_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_AUDIO = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a", "audio/x-m4a"}


def _owned(db: Session, user: User, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/{project_id}/uploads/text", response_model=ProjectOut)
@limiter.limit("10/minute")
async def upload_text(
    request: Request,
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _owned(db, user, project_id)
    data = await file.read()
    if len(data) > MAX_TEXT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Text file too large (10 MB max)")
    key = f"uploads/{project_id}/article_{file.filename}"
    upload_bytes(key, data, content_type=file.content_type or "text/plain")
    project.source_text_key = key
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/uploads/audio", response_model=ProjectOut)
@limiter.limit("10/minute")
async def upload_audio(
    request: Request,
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
