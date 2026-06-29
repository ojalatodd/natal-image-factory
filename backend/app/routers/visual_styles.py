"""Router that exposes visual style presets for the frontend picker."""
from fastapi import APIRouter

from app.schemas import VisualStyleOut
from app.visual_styles import serialize_visual_styles

router = APIRouter(prefix="/visual-styles", tags=["visual_styles"])


@router.get("", response_model=list[VisualStyleOut])
def list_visual_styles() -> list[VisualStyleOut]:
    return serialize_visual_styles()
