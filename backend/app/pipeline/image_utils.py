"""Image normalization helpers using Pillow.

Resizes, converts format, and prepares still images for the output package.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

MAX_WIDTH = 1920
MAX_HEIGHT = 1080
THUMBNAIL_WIDTH = 400
JPEG_QUALITY = 90


def normalize_image(
    src: Path,
    dest: Path,
    *,
    max_width: int = MAX_WIDTH,
    max_height: int = MAX_HEIGHT,
) -> tuple[int, int]:
    """Resize and convert image to JPEG. Returns (width, height) of the result."""
    img = Image.open(src)
    img = img.convert("RGB")

    # Preserve aspect ratio, fit within max dimensions
    img.thumbnail((max_width, max_height), Image.LANCZOS)

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=JPEG_QUALITY)
    return img.width, img.height


def make_thumbnail(src: Path, dest: Path, *, width: int = THUMBNAIL_WIDTH) -> Path:
    """Create a small thumbnail for the UI."""
    img = Image.open(src)
    img = img.convert("RGB")
    img.thumbnail((width, width), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=80)
    return dest


def image_to_bytes(src: Path, *, max_width: int = MAX_WIDTH, max_height: int = MAX_HEIGHT) -> tuple[bytes, int, int]:
    """Normalize image and return as bytes (for Spaces upload). Returns (data, width, height)."""
    img = Image.open(src)
    img = img.convert("RGB")
    img.thumbnail((max_width, max_height), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=JPEG_QUALITY)
    return buf.getvalue(), img.width, img.height


def thumbnail_to_bytes(src: Path, *, width: int = THUMBNAIL_WIDTH) -> bytes:
    """Create thumbnail and return as bytes."""
    img = Image.open(src)
    img = img.convert("RGB")
    img.thumbnail((width, width), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return buf.getvalue()
