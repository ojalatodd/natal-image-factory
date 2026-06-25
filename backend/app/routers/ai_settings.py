from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import AiProvider, AiSettings, User
from app.schemas import AiConfigIn, AiConfigOut

router = APIRouter(prefix="/settings/ai", tags=["ai-settings"])

DEFAULT_CONFIG = {
    "provider": AiProvider.openai,
    "model": "gpt-4o-mini",
    "vision_model": "gpt-4o",
    "image_model": "dall-e-3",
}


def _ensure_config(db: Session, user: User) -> AiSettings:
    config = db.query(AiSettings).filter(AiSettings.user_id == user.id).first()
    if config:
        return config

    config = AiSettings(user_id=user.id, **DEFAULT_CONFIG)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("", response_model=AiConfigOut)
def get_ai_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _ensure_config(db, user)


@router.put("", response_model=AiConfigOut)
def update_ai_settings(
    body: AiConfigIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    config = _ensure_config(db, user)
    config.provider = body.provider
    config.model = body.model
    config.vision_model = body.vision_model
    config.image_model = body.image_model
    db.commit()
    db.refresh(config)
    return config
