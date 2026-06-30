"""Wikimedia Commons video adapter — public domain / CC videos.

Uses the Wikimedia Commons API (no key required) to search for video
files (.ogv, .webm, .mp4) matching a query. Returns candidates with
thumbnails and metadata.
"""
from __future__ import annotations

import logging
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_exponential

from app.pipeline.adapters.base import CandidateAsset, http_client, register

logger = logging.getLogger("natal")

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_THUMB = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width=400"
COMMONS_FULL = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"

VIDEO_EXTENSIONS = (".ogv", ".webm", ".mp4")


class WikimediaCommonsVideoAdapter:
    name = "Wikimedia Commons Video"
    media_type = "video"  # type: ignore[assignment]
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

        # Use filetype filter to find only video files on Wikimedia Commons
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"{enhanced_query} filetype:video",
            "srnamespace": 6,  # File namespace
            "srlimit": str(limit * 5),  # over-fetch since we filter by extension
        }

        async with http_client(timeout=30) as client:
            resp = await client.get(COMMONS_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        search_results = data.get("query", {}).get("search", [])
        candidates: list[CandidateAsset] = []

        for result in search_results:
            title = result.get("title", "")
            if not title.startswith("File:"):
                continue
            filename = title[len("File:"):]

            lower = filename.lower()
            if not any(lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
                continue

            thumb_url = COMMONS_THUMB.format(filename=filename.replace(" ", "_"))
            full_url = COMMONS_FULL.format(filename=filename.replace(" ", "_"))

            candidates.append(
                CandidateAsset(
                    source_name=self.name,
                    media_type="video",
                    source_url=f"https://commons.wikimedia.org/wiki/{title}",
                    thumbnail_url=thumb_url,
                    download_url=full_url,
                    license=self.license_default,
                    attribution=f"Wikimedia Commons: {title}",
                    title=filename,
                )
            )

            if len(candidates) >= limit:
                break

        return candidates[:limit]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch(self, asset: CandidateAsset, dest: Path) -> Path:
        url = asset.download_url or asset.source_url
        async with http_client(timeout=120, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
        return dest


register(WikimediaCommonsVideoAdapter())
