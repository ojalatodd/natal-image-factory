"""Pexels video adapter — free stock videos.

Uses the Pexels Videos API. Requires an API key (free tier available at
https://www.pexels.com/api/). When no key is configured, search returns
an empty list and the adapter is effectively disabled.
"""
from __future__ import annotations

import logging
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.pipeline.adapters.base import CandidateAsset, http_client, register

logger = logging.getLogger("natal")

PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"


class PexelsVideoAdapter:
    name = "Pexels"
    media_type = "video"  # type: ignore[assignment]
    license_default = "Pexels License (free to use)"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def search(
        self,
        query: str,
        *,
        style: str = "",
        min_duration_s: float | None = None,
        limit: int = 10,
    ) -> list[CandidateAsset]:
        api_key = settings.pexels_api_key
        if not api_key:
            logger.debug("Pexels API key not configured — skipping search")
            return []

        enhanced_query = f"{query} {style}".strip() if style and style != "ai_judgement" else query

        params = {
            "query": enhanced_query,
            "per_page": str(limit),
            "orientation": "landscape",
        }

        async with http_client(timeout=30) as client:
            resp = await client.get(
                PEXELS_VIDEO_SEARCH,
                params=params,
                headers={"Authorization": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        videos = data.get("videos", [])
        candidates: list[CandidateAsset] = []

        for video in videos:
            # Pick the best HD file (prefer 1280x720 or larger)
            files = video.get("video_files", [])
            best_file = None
            for f in files:
                w = f.get("width", 0)
                if w >= 1280:
                    best_file = f
                    break
            if not best_file and files:
                best_file = files[0]
            if not best_file:
                continue

            duration_s = float(video.get("duration", 0))
            thumb_url = video.get("image", "")  # Pexels provides a poster image

            candidates.append(
                CandidateAsset(
                    source_name=self.name,
                    media_type="video",
                    source_url=video.get("url", ""),
                    thumbnail_url=thumb_url,
                    download_url=best_file.get("link", ""),
                    license=self.license_default,
                    attribution=f"Pexels: {video.get('user', {}).get('name', 'Unknown')}",
                    title=video.get("url", "").split("/")[-1],
                    duration_s=duration_s,
                    width=best_file.get("width"),
                    height=best_file.get("height"),
                )
            )

        return candidates[:limit]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch(self, asset: CandidateAsset, dest: Path) -> Path:
        url = asset.download_url or asset.source_url
        if not url:
            raise ValueError(f"No download URL for asset from {self.name}")
        async with http_client(timeout=120, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
        return dest


register(PexelsVideoAdapter())
