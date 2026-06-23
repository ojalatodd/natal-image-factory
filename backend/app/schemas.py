from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import AssetStatus, MediaMix, MediaType, ProjectStatus


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


# ---- Projects ----
class ProjectCreate(BaseModel):
    name: str


class ProjectSettings(BaseModel):
    media_mix: MediaMix | None = None
    visual_style: str | None = None
    ai_images_enabled: bool | None = None
    ai_video_motion: bool | None = None


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
    created_at: datetime
    updated_at: datetime


# ---- Assets / Segments ----
class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    media_type: MediaType
    source_name: str
    source_url: str | None
    license: str | None
    attribution: str | None
    thumbnail_key: str | None
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


class DownloadOut(BaseModel):
    url: str
