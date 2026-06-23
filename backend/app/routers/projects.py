from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Project, ProjectStatus, User
from app.schemas import DownloadOut, ProjectCreate, ProjectOut, ProjectSettings
from app.storage import presigned_url
from app.tasks import run_pipeline

router = APIRouter(prefix="/projects", tags=["projects"])


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


@router.get("/{project_id}/download", response_model=DownloadOut)
def download(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = _owned(db, user, project_id)
    if project.status not in (ProjectStatus.complete, ProjectStatus.review):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package not ready")
    return DownloadOut(url=presigned_url(f"output/project_{project.id}.zip"))
