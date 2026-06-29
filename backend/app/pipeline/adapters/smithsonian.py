"""Smithsonian Open Access source adapter — public domain images.

Uses the Smithsonian Open Access API to search for public-domain images
across Smithsonian museums. API key is free but optional for basic search.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.pipeline.adapters.base import CandidateAsset, http_client, register

logger = logging.getLogger("natal")

SMITHSONIAN_API = "https://api.si.edu/openaccess/api/v1.0"


class SmithsonianAdapter:
    name = "Smithsonian Open Access"
    media_type = "still"  # type: ignore[assignment]
    license_default = "CC0 (Smithsonian Open Access)"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def search(
        self,
        query: str,
        *,
        style: str = "",
        min_duration_s: float | None = None,
        limit: int = 10,
    ) -> list[CandidateAsset]:
        # Use the default API key if none configured
        api_key = getattr(settings, "smithsonian_api_key", None) or "demo"

        params = {
            "q": query,
            "rows": str(limit),
            "fq": "type:emuseum AND media_usage:CC0",
            "api_key": api_key,
        }

        async with http_client(timeout=30) as client:
            resp = await client.get(f"{SMITHSONIAN_API}/content/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        rows = data.get("response", {}).get("rows", [])
        candidates: list[CandidateAsset] = []

        for row in rows:
            content = row.get("content", {})
            descriptive = content.get("descriptiveRevealed", {})
            title = descriptive.get("title", "")
            notes = descriptive.get("notes", {})
            note_text = notes.get("notesContent", [""])[0] if isinstance(notes.get("notesContent"), list) else ""

            # Find image URLs in media
            media = content.get("media", {})
            media_list = media.get("mediaResources", []) if isinstance(media, dict) else []
            image_url = None
            thumb_url = None

            for m in media_list:
                if m.get("type") == "Images":
                    image_url = m.get("contentUrl") or m.get("url")
                    thumb_url = m.get("thumbnailUrl") or m.get("contentUrl")
                    break

            if not image_url:
                continue

            candidates.append(
                CandidateAsset(
                    source_name=self.name,
                    media_type="still",
                    source_url=row.get("url", ""),
                    thumbnail_url=thumb_url or image_url,
                    download_url=image_url,
                    license=self.license_default,
                    attribution=f"Smithsonian: {title}",
                    title=title,
                )
            )

        return candidates[:limit]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch(self, asset: CandidateAsset, dest: Path) -> Path:
        url = asset.download_url or asset.thumbnail_url
        if not url:
            raise ValueError(f"No download URL for asset from {self.name}")
        async with http_client(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
        return dest


register(SmithsonianAdapter())
