from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models import AiProvider, AssetStatus, MediaMix, MediaType, ProjectStatus, UserRole
from app.visual_styles import is_valid_visual_style


# ---- Auth ----
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    role: UserRole


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ---- Admin ----
class AdminCreateUser(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.user


class AdminUpdateRole(BaseModel):
    role: UserRole


class AdminResetPassword(BaseModel):
    new_password: str


# ---- Visual styles ----
class VisualStyleOut(BaseModel):
    value: str
    label: str
    summary: str
    prompt: str


# ---- Projects ----
class ProjectCreate(BaseModel):
    name: str


class ProjectSettings(BaseModel):
    media_mix: MediaMix | None = None
    visual_style: str | None = None
    ai_images_enabled: bool | None = None
    ai_video_motion: bool | None = None

    @field_validator("visual_style")
    @classmethod
    def validate_visual_style(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not is_valid_visual_style(value):
            raise ValueError("Invalid visual style preset")
        return value


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    status: ProjectStatus
    media_mix: MediaMix
    visual_style: str
    ai_images_enabled: bool
    ai_video_motion: bool
    audio_duration_s: float | None
    source_audio_key: str | None
    source_text_key: str | None
    created_at: datetime
    updated_at: datetime


# ---- Assets / Segments ----
class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    media_type: MediaType
    source_name: str
    source_url: str | None
    download_url: str | None
    license: str | None
    attribution: str | None
    thumbnail_url: str | None
    thumbnail_key: str | None
    spaces_key: str | None
    video_key: str | None
    width: int | None
    height: int | None
    duration_s: float | None
    relevance_score: float | None
    is_chosen: bool
    status: AssetStatus


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    index: int
    start_s: float
    end_s: float
    duration_s: float
    theme_label: str | None
    summary: str | None
    chosen_media_type: MediaType | None
    chosen_asset_id: int | None
    assets: list[AssetOut] = []


class SegmentSwap(BaseModel):
    media_type: MediaType | None = None
    asset_id: int | None = None


# ---- Jobs ----
class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    stage: str
    progress_pct: int
    message: str | None
    error: str | None


# ---- Sources ----
class SourceConfigIn(BaseModel):
    source_name: str
    media_type: MediaType
    enabled: bool = True
    priority: int = 100


class SourceConfigOut(SourceConfigIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---- AI Settings ----
class AiConfigIn(BaseModel):
    provider: AiProvider
    model: str
    vision_model: str | None = None
    image_model: str | None = None


class AiConfigOut(AiConfigIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DownloadOut(BaseModel):
    url: str


# ---- Cost Estimate ----
class CostEstimateOut(BaseModel):
    whisper_usd: float
    segmentation_usd: float
    ranking_usd: float
    dalle_fallback_usd: float
    total_usd: float
    estimated_segments: int
    audio_minutes: float
