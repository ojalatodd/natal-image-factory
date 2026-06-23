"""The six pipeline stages.

Phase 0 provides working orchestration with safe stubs:
- Stage 1 (transcribe) produces a single placeholder timeline entry.
- Stage 2 (segment) creates demo segments so the UI + packaging are exercisable.
- Stages 3-6 are wired but defer real source/AI/ffmpeg work to later phases.

Each stage updates progress and is independently testable.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app import progress
from app.models import MediaType, Project, Segment


# ---- Stage 1: Transcribe & align (Whisper) ----
def transcribe(db: Session, project: Project) -> dict:
    progress.publish(project.id, "transcribe", 10, "Transcribing voiceover…")
    # Phase 1: call OpenAI Whisper on project.source_audio_key, return word timeline.
    duration = project.audio_duration_s or 0.0
    return {"duration_s": duration, "words": []}


# ---- Stage 2: Semantic segmentation (GPT-4o) ----
def segment(db: Session, project: Project, transcript: dict) -> list[Segment]:
    progress.publish(project.id, "segment", 30, "Finding thematic segments…")
    # Phase 1: GPT-4o over article text + transcript. Placeholder: one segment.
    duration = transcript.get("duration_s") or 0.0
    seg = Segment(
        project_id=project.id,
        index=1,
        start_s=0.0,
        end_s=duration,
        duration_s=duration,
        theme_label="Full narration",
        summary="Placeholder segment — real segmentation lands in Phase 1.",
        search_query=project.name,
    )
    db.add(seg)
    db.commit()
    db.refresh(seg)
    return [seg]


# ---- Stage 3: Media search (stills + video) ----
def search_media(db: Session, project: Project, segments: list[Segment]) -> None:
    progress.publish(project.id, "search", 50, "Searching public-domain sources…")
    # Phase 1 (stills) + Phase 3 (video): query adapters per media-mix policy.


# ---- Stage 4: Rank & match (GPT-4o Vision) ----
def rank_match(db: Session, project: Project, segments: list[Segment]) -> None:
    progress.publish(project.id, "rank", 65, "Ranking candidate media…")
    # Phase 1/3: score candidates; set chosen_media_type + chosen_asset_id.
    for seg in segments:
        seg.chosen_media_type = MediaType.still
    db.commit()


# ---- Stage 5: Acquire, trim & normalize (ffmpeg) ----
def acquire_process(db: Session, project: Project, segments: list[Segment]) -> None:
    progress.publish(project.id, "process", 80, "Preparing media (trim/normalize)…")
    # Phase 1 (stills) + Phase 3 (video trim/normalize via media.py).


# ---- Stage 6: Package ZIP + manifest ----
def package(db: Session, project: Project, segments: list[Segment]) -> str:
    progress.publish(project.id, "package", 95, "Packaging download…")
    # Phase 1: build numbered files + manifest.txt, zip, upload to Spaces output/.
    return f"output/project_{project.id}.zip"
