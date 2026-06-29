from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import SourceAdapterConfig, User
from app.schemas import SourceConfigIn, SourceConfigOut

router = APIRouter(prefix="/settings/sources", tags=["sources"])

# Default curated catalog surfaced to the UI until the user customizes it.
DEFAULT_CATALOG = [
    {"source_name": "Library of Congress", "media_type": "still", "priority": 10},
    {"source_name": "Wikimedia Commons", "media_type": "still", "priority": 20},
    {"source_name": "The Met", "media_type": "still", "priority": 30},
    {"source_name": "Smithsonian Open Access", "media_type": "still", "priority": 40},
    {"source_name": "Europeana", "media_type": "still", "priority": 50},
    {"source_name": "Wikimedia Commons Video", "media_type": "video", "priority": 10},
    {"source_name": "Internet Archive", "media_type": "video", "priority": 20},
    {"source_name": "National Archives (NARA)", "media_type": "video", "priority": 30},
    {"source_name": "NASA", "media_type": "video", "priority": 40},
    {"source_name": "Pexels", "media_type": "video", "priority": 50},
]


@router.get("", response_model=list[SourceConfigOut])
def list_sources(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    configs = db.query(SourceAdapterConfig).filter(SourceAdapterConfig.user_id == user.id).all()
    return configs


@router.put("", response_model=list[SourceConfigOut])
def upsert_sources(
    items: list[SourceConfigIn],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db.query(SourceAdapterConfig).filter(SourceAdapterConfig.user_id == user.id).delete()
    for item in items:
        db.add(SourceAdapterConfig(user_id=user.id, **item.model_dump()))
    db.commit()
    return db.query(SourceAdapterConfig).filter(SourceAdapterConfig.user_id == user.id).all()
