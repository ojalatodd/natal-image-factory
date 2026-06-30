from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    processing = "processing"
    review = "review"
    complete = "complete"
    error = "error"


class MediaMix(str, enum.Enum):
    stills = "stills"
    video = "video"
    balanced = "balanced"
    ai_judgement = "ai_judgement"


class MediaType(str, enum.Enum):
    still = "still"
    video = "video"


class AiProvider(str, enum.Enum):
    openai = "openai"
    anthropic = "anthropic"
    gemini = "gemini"
    deepseek = "deepseek"


class AssetStatus(str, enum.Enum):
    candidate = "candidate"
    downloaded = "downloaded"
    processed = "processed"
    failed = "failed"


class UserRole(enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    projects: Mapped[list[Project]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.draft)

    # Settings
    media_mix: Mapped[MediaMix] = mapped_column(Enum(MediaMix), default=MediaMix.balanced)
    visual_style: Mapped[str] = mapped_column(String(64), default="ai_judgement")
    ai_images_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_video_motion: Mapped[bool] = mapped_column(Boolean, default=True)

    # Uploaded sources (Spaces keys)
    source_audio_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_text_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    audio_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="projects")
    segments: Mapped[list[Segment]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Segment.index"
    )
    jobs: Mapped[list[Job]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    index: Mapped[int] = mapped_column(Integer)

    start_s: Mapped[float] = mapped_column(Float)
    end_s: Mapped[float] = mapped_column(Float)
    duration_s: Mapped[float] = mapped_column(Float)

    theme_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_query: Mapped[str | None] = mapped_column(Text, nullable=True)

    chosen_media_type: Mapped[MediaType | None] = mapped_column(Enum(MediaType), nullable=True)
    chosen_asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)

    project: Mapped[Project] = relationship(back_populates="segments")
    assets: Mapped[list[Asset]] = relationship(
        back_populates="segment",
        cascade="all, delete-orphan",
        foreign_keys="Asset.segment_id",
    )


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("segments.id"))
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType))

    source_name: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    download_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text, nullable=True)

    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    spaces_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)

    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_chosen: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus), default=AssetStatus.candidate)

    segment: Mapped[Segment] = relationship(back_populates="assets", foreign_keys=[segment_id])


class SourceAdapterConfig(Base):
    __tablename__ = "source_adapter_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    source_name: Mapped[str] = mapped_column(String(128))
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)


class AiSettings(Base):
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    provider: Mapped[AiProvider] = mapped_column(Enum(AiProvider), default=AiProvider.openai)
    model: Mapped[str] = mapped_column(String(128), default="gpt-4o-mini")
    vision_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    image_model: Mapped[str | None] = mapped_column(String(128), nullable=True)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    stage: Mapped[str] = mapped_column(String(64))
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project: Mapped[Project] = relationship(back_populates="jobs")
