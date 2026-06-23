"""ffmpeg / ffprobe helpers for the video b-roll engine.

Full duration-aware fitting, sub-clip extraction, normalization, and the
"Motion from Stills" (Ken Burns) effect are implemented in Phases 3-4.
These signatures define the contract used by the pipeline.
"""
from __future__ import annotations

import shutil
from pathlib import Path


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def probe_duration(path: Path) -> float:
    """Return media duration in seconds via ffprobe."""
    import ffmpeg  # imported lazily so the module loads without the binary in dev

    meta = ffmpeg.probe(str(path))
    return float(meta["format"]["duration"])


def trim_and_normalize(
    src: Path,
    dest: Path,
    *,
    start_s: float,
    duration_s: float,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> Path:
    """Extract a sub-clip, strip audio, and normalize to a common format.

    Placeholder: Phase 3 wires the full ffmpeg invocation described in
    Technical-Implementation-Plan.md §7.2.
    """
    raise NotImplementedError("Video trim/normalize lands in Phase 3")


def ken_burns_from_still(
    src: Path,
    dest: Path,
    *,
    duration_s: float,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> Path:
    """Produce a slow pan/zoom MP4 from a still image (Phase 4)."""
    raise NotImplementedError("Ken Burns motion lands in Phase 4")
