"""Library of Congress source adapter — public domain images.

Uses the loc.gov API to search for public-domain images from the
Library of Congress collections. No API key required.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.pipeline.adapters.base import CandidateAsset, http_client, register

logger = logging.getLogger("natal")

LOC_API = "https://www.loc.gov"


class LibraryOfCongressAdapter:
    name = "Library of Congress"
    media_type = "still"  # type: ignore[assignment]
    license_default = "Public Domain"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def search(
        self,
        query: str,
        *,
        style: str = "",
        min_duration_s: float | None = None,
        limit: int = 10,
    ) -> list[CandidateAsset]:
        enhanced_query = f"{query} {style}".strip() if style and style != "ai_judgement" else query

        params = {
            "q": enhanced_query,
            "fo": "json",
            "fa": "partof:photos",
            "c": str(limit),
        }

        async with http_client(timeout=30) as client:
            resp = await client.get(f"{LOC_API}/search/", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        candidates: list[CandidateAsset] = []

        for item in results:
            # Skip collections and web pages
            if item.get("format") and "collection" in str(item.get("format", "")):
                continue

            image_url = item.get("image_url")
            if not image_url:
                continue
            if isinstance(image_url, list):
                image_url = image_url[0] if image_url else None
            if not image_url:
                continue

            thumb_url = item.get("image_url")
            if isinstance(thumb_url, list):
                thumb_url = thumb_url[0]

            candidates.append(
                CandidateAsset(
                    source_name=self.name,
                    media_type="still",
                    source_url=item.get("url", LOC_API),
                    thumbnail_url=thumb_url or image_url,
                    download_url=image_url,
                    license=self.license_default,
                    attribution=f"Library of Congress: {item.get('title', '')}",
                    title=item.get("title", ""),
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


register(LibraryOfCongressAdapter())
