"""Internet Archive source adapter — public domain images and texts.

Uses the archive.org Advanced Search API to find public-domain images.
No API key required.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.pipeline.adapters.base import CandidateAsset, register

logger = logging.getLogger("natal")

IA_SEARCH = "https://archive.org/advancedsearch.php"
IA_DETAIL = "https://archive.org/details/{identifier}"
IA_DOWNLOAD = "https://archive.org/download/{identifier}/{filename}"


class InternetArchiveAdapter:
    name = "Internet Archive"
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
            "q": f'({enhanced_query}) AND mediatype:(texts OR image)',
            "fl[]": ["identifier", "title", "date", "creator"],
            "rows": str(limit),
            "output": "json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(IA_SEARCH, params=params)
            resp.raise_for_status()
            data = resp.json()

        docs = data.get("response", {}).get("docs", [])
        candidates: list[CandidateAsset] = []

        for doc in docs:
            identifier = doc.get("identifier", "")
            if not identifier:
                continue

            # Use the item thumbnail from archive.org
            thumb_url = f"https://archive.org/services/img/{identifier}"
            detail_url = IA_DETAIL.format(identifier=identifier)

            candidates.append(
                CandidateAsset(
                    source_name=self.name,
                    media_type="still",
                    source_url=detail_url,
                    thumbnail_url=thumb_url,
                    download_url=thumb_url,
                    license=self.license_default,
                    attribution=f"Internet Archive: {doc.get('title', identifier)}",
                    title=doc.get("title", identifier),
                )
            )

        return candidates[:limit]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch(self, asset: CandidateAsset, dest: Path) -> Path:
        url = asset.download_url or asset.thumbnail_url
        if not url:
            raise ValueError(f"No download URL for asset from {self.name}")
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
        return dest


register(InternetArchiveAdapter())
