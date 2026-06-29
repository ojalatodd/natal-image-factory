"""Internet Archive video adapter — public domain videos and newsreels.

Uses the archive.org Advanced Search API to find public-domain video
items (mediatype=movies). No API key required.
"""
from __future__ import annotations

import logging
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_exponential

from app.pipeline.adapters.base import CandidateAsset, http_client, register

logger = logging.getLogger("natal")

IA_SEARCH = "https://archive.org/advancedsearch.php"
IA_DETAIL = "https://archive.org/details/{identifier}"
IA_METADATA = "https://archive.org/metadata/{identifier}"
IA_DOWNLOAD = "https://archive.org/download/{identifier}/{filename}"


class InternetArchiveVideoAdapter:
    name = "Internet Archive Video"
    media_type = "video"  # type: ignore[assignment]
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
            "q": f"({enhanced_query}) AND mediatype:(movies)",
            "fl[]": ["identifier", "title", "date", "creator", "duration"],
            "rows": str(limit),
            "output": "json",
        }

        async with http_client(timeout=30) as client:
            resp = await client.get(IA_SEARCH, params=params)
            resp.raise_for_status()
            data = resp.json()

        docs = data.get("response", {}).get("docs", [])
        candidates: list[CandidateAsset] = []

        for doc in docs:
            identifier = doc.get("identifier", "")
            if not identifier:
                continue

            thumb_url = f"https://archive.org/services/img/{identifier}"
            detail_url = IA_DETAIL.format(identifier=identifier)

            # Parse duration if available (IA returns seconds as string)
            duration_s = None
            raw_duration = doc.get("duration")
            if raw_duration:
                try:
                    duration_s = float(raw_duration)
                except (ValueError, TypeError):
                    pass

            candidates.append(
                CandidateAsset(
                    source_name=self.name,
                    media_type="video",
                    source_url=detail_url,
                    thumbnail_url=thumb_url,
                    download_url=None,  # Resolved in fetch() via metadata API
                    license=self.license_default,
                    attribution=f"Internet Archive: {doc.get('title', identifier)}",
                    title=doc.get("title", identifier),
                    duration_s=duration_s,
                    extra={"identifier": identifier},
                )
            )

        return candidates[:limit]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch(self, asset: CandidateAsset, dest: Path) -> Path:
        identifier = asset.extra.get("identifier")
        if not identifier:
            raise ValueError(f"No Internet Archive identifier for asset from {self.name}")

        # Fetch item metadata to find the best video file
        async with http_client(timeout=30, follow_redirects=True) as client:
            meta_resp = await client.get(IA_METADATA.format(identifier=identifier))
            meta_resp.raise_for_status()
            metadata = meta_resp.json()

        files = metadata.get("files", [])
        # Prefer .mp4, then .ogv, then .webm
        video_file = None
        for ext in (".mp4", ".ogv", ".webm"):
            for f in files:
                name = f.get("name", "").lower()
                if name.endswith(ext):
                    video_file = f
                    break
            if video_file:
                break

        if not video_file:
            raise ValueError(f"No video file found in Internet Archive item {identifier}")

        filename = video_file["name"]
        download_url = IA_DOWNLOAD.format(identifier=identifier, filename=filename)

        async with http_client(timeout=120, follow_redirects=True) as client:
            resp = await client.get(download_url)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
        return dest


register(InternetArchiveVideoAdapter())
