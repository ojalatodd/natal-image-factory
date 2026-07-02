"""ffmpeg / ffprobe helpers for the video b-roll engine.

Full duration-aware fitting, sub-clip extraction, normalization, and the
"Motion from Stills" (Ken Burns) effect.
"""
from __future__ import annotations

import logging
import random
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("natal")


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

    - Seeks to start_s, extracts duration_s seconds
    - Scales to fit within width x height (preserving aspect ratio, padding if needed)
    - Converts to H.264, yuv420p, 30fps, faststart
    - Strips audio (voiceover is mixed separately in the final edit)
    """
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg not available in this environment")

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_s:.3f}",
        "-i", str(src),
        "-t", f"{duration_s:.3f}",
        "-an",
        "-vf", (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"fps={fps}"
        ),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "23",
        "-movflags", "+faststart",
        str(dest),
    ]

    logger.info(
        "trim_and_normalize: %s -> %s (start=%.1fs, dur=%.1fs, %dx%d@%dfps)",
        src.name, dest.name, start_s, duration_s, width, height, fps,
    )

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        # Log full error with file details
        logger.error(
            "FFmpeg failed for %s (src=%s, dest=%s, start=%.1fs, dur=%.1fs)\n"
            "STDERR:\n%s\nSTDOUT:\n%s",
            src.name, src, dest, start_s, duration_s, result.stderr, result.stdout,
        )
        # Try a simpler fallback: just copy the stream without complex filters
        logger.info("Attempting simpler FFmpeg copy as fallback...")
        fallback_cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start_s:.3f}",
            "-i", str(src),
            "-t", f"{duration_s:.3f}",
            "-an",
            "-c:v", "copy",
            str(dest),
        ]
        fallback_result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=300)
        if fallback_result.returncode != 0:
            logger.error(
                "FFmpeg fallback also failed for %s\nSTDERR:\n%s",
                src.name, fallback_result.stderr,
            )
            raise RuntimeError(
                f"FFmpeg failed (both complex and simple copy). "
                f"File: {src.name}, size: {src.stat().st_size if src.exists() else 0} bytes. "
                f"Error: {result.stderr[-500:]}"
            )
        logger.info("FFmpeg fallback copy succeeded for %s", src.name)

    return dest


def ken_burns_from_still(
    src: Path,
    dest: Path,
    *,
    duration_s: float,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> Path:
    """Produce a slow pan/zoom MP4 from a still image using ffmpeg zoompan.

    Randomly selects a zoom direction (in, out) and pan direction to create
    variety across segments. The output is an H.264 MP4 at the given resolution.
    """
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg not available in this environment")

    total_frames = int(duration_s * fps)
    # Zoom range: 1.0 to 1.3 (30% zoom) — subtle, documentary-style
    zoom_start = 1.0
    zoom_end = 1.3

    # Randomly choose zoom in or out
    zoom_in = random.choice([True, False])
    if not zoom_in:
        zoom_start, zoom_end = zoom_end, zoom_start

    # Pan direction: pick a random target corner/center offset
    pan_options = ["left", "right", "up", "down", "center"]
    pan_dir = random.choice(pan_options)

    # Build zoompan filter expressions
    # z = zoom factor at frame i, x/y = pan position
    if zoom_in:
        z_expr = f"min(zoom+{(zoom_end - zoom_start) / total_frames:.8f},{zoom_end})"
    else:
        z_expr = f"if(eq(on,0),{zoom_start},max(zoom-{(zoom_start - zoom_end) / total_frames:.8f},{zoom_end}))"

    # Pan positions (centered by default, offset by direction)
    pan_x = "iw/2-(iw/zoom/2)"
    pan_y = "ih/2-(ih/zoom/2)"
    if pan_dir == "left":
        pan_x = "0"
    elif pan_dir == "right":
        pan_x = "iw-iw/zoom"
    elif pan_dir == "up":
        pan_y = "0"
    elif pan_dir == "down":
        pan_y = "ih-ih/zoom"

    # zoompan filter: upscale input first to avoid pixelation, then apply zoom/pan
    # The 'd' parameter sets how many frames the effect lasts
    filter_complex = (
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
        f"crop={width * 2}:{height * 2},"
        f"zoompan=z='{z_expr}':x='{pan_x}':y='{pan_y}':"
        f"d={total_frames}:s={width}x{height}:fps={fps}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(src),
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-t", f"{duration_s:.3f}",
        "-r", str(fps),
        "-preset", "fast",
        "-crf", "23",
        "-movflags", "+faststart",
        str(dest),
    ]

    logger.info("Ken Burns: %s -> %s (%.1fs, %d frames, zoom_%s pan_%s)",
                src.name, dest.name, duration_s, total_frames,
                "in" if zoom_in else "out", pan_dir)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error(
            "Ken Burns FFmpeg failed for %s (src=%s, dest=%s, dur=%.1fs)\n"
            "STDERR:\n%s\nSTDOUT:\n%s",
            src.name, src, dest, duration_s, result.stderr, result.stdout,
        )
        raise RuntimeError(
            f"Ken Burns FFmpeg failed. File: {src.name}, size: {src.stat().st_size if src.exists() else 0} bytes. "
            f"Error: {result.stderr[-500:]}"
        )

    return dest


def extract_thumbnail(
    src: Path,
    dest: Path,
    *,
    at_s: float = 1.0,
    width: int = 320,
) -> Path:
    """Extract a single frame from a video as a JPEG thumbnail.

    Seeks to at_s (default 1s to avoid black fade-in frames) and captures
    a single frame scaled to width pixels (preserving aspect ratio).
    """
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg not available in this environment")

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{at_s:.3f}",
        "-i", str(src),
        "-frames:v", "1",
        "-vf", f"scale={width}:-1",
        "-q:v", "3",
        str(dest),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        logger.error(
            "Thumbnail FFmpeg failed for %s (src=%s, dest=%s, at=%.1fs)\n"
            "STDERR:\n%s\nSTDOUT:\n%s",
            src.name, src, dest, at_s, result.stderr, result.stdout,
        )
        raise RuntimeError(
            f"Thumbnail FFmpeg failed. File: {src.name}, size: {src.stat().st_size if src.exists() else 0} bytes. "
            f"Error: {result.stderr[-500:]}"
        )

    return dest
