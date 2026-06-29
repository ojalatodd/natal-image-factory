"""Wikimedia Commons source adapter — public domain / CC images.

Uses the Wikimedia Commons API (no key required) to search for images
matching a query. Returns candidates with thumbnails and metadata.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.pipeline.adapters.base import HEADERS, CandidateAsset, register

logger = logging.getLogger("natal")

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_THUMB = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width=400"
COMMONS_FULL = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"


class WikimediaCommonsAdapter:
    name = "Wikimedia Commons"
    media_type = "still"  # type: ignore[assignment]
    license_default = "Public Domain / CC"

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
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": enhanced_query,
            "srnamespace": 6,  # File namespace
            "srlimit": str(limit),
        }

        async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
            resp = await client.get(COMMONS_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        search_results = data.get("query", {}).get("search", [])
        candidates: list[CandidateAsset] = []

        for result in search_results:
            title = result.get("title", "")
            if not title.startswith("File:"):
                continue
            filename = title[len("File:") :]

            # Skip non-image formats
            lower = filename.lower()
            if any(lower.endswith(ext) for ext in [".pdf", ".svg", ".ogg", ".ogv", ".webm", ".mp4"]):
                continue

            thumb_url = COMMONS_THUMB.format(filename=filename.replace(" ", "_"))
            full_url = COMMONS_FULL.format(filename=filename.replace(" ", "_"))

            candidates.append(
                CandidateAsset(
                    source_name=self.name,
                    media_type="still",
                    source_url=f"https://commons.wikimedia.org/wiki/{title}",
                    thumbnail_url=thumb_url,
                    download_url=full_url,
                    license=self.license_default,
                    attribution=f"Wikimedia Commons: {title}",
                    title=filename,
                )
            )

        return candidates[:limit]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch(self, asset: CandidateAsset, dest: Path) -> Path:
        url = asset.download_url or asset.thumbnail_url
        async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers=HEADERS) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
        return dest


register(WikimediaCommonsAdapter())
