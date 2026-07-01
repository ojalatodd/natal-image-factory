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

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "for", "with",
    "by", "from", "as", "history", "historical", "footage", "video", "scene",
}


def _broadened_queries(query: str) -> list[str]:
    """Build progressively broader queries, most specific first.

    Wikimedia Commons has a sparse video library, so specific multi-word
    queries often match nothing. We retry with fewer leading keywords
    (the AI places the key subject first) until we find results.
    """
    words = [w for w in query.split() if w]
    meaningful = [w for w in words if w.lower() not in _STOPWORDS]
    base = meaningful or words

    attempts: list[str] = []
    # Full original query first, then progressively fewer leading keywords.
    for candidate in (query, *(" ".join(base[:n]) for n in (3, 2, 1))):
        candidate = candidate.strip()
        if candidate and candidate not in attempts:
            attempts.append(candidate)
    return attempts


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
        base_query = f"{query} {style}".strip() if style and style != "ai_judgement" else query

        # Wikimedia's video library is sparse; try the specific query first,
        # then progressively broader ones until we find video candidates.
        for attempt in _broadened_queries(base_query):
            candidates = await self._search_once(attempt, limit=limit)
            if candidates:
                if attempt != base_query:
                    logger.info(
                        "Wikimedia video: broadened %r -> %r (%d results)",
                        base_query, attempt, len(candidates),
                    )
                return candidates
        return []

    async def _search_once(self, query: str, *, limit: int) -> list[CandidateAsset]:
        # Use filetype filter to find only video files on Wikimedia Commons
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"{query} filetype:video",
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
        max_bytes = 500 * 1024 * 1024  # 500 MB — skip huge 4K files
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with http_client(timeout=300, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                content_length = int(resp.headers.get("content-length", 0))
                if content_length and content_length > max_bytes:
                    raise ValueError(
                        f"Video file too large ({content_length // 1024 // 1024} MB), skipping"
                    )
                written = 0
                with open(dest, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        written += len(chunk)
                        if written > max_bytes:
                            f.close()
                            dest.unlink(missing_ok=True)
                            raise ValueError("Video file exceeded 500 MB during download, skipping")
                        f.write(chunk)
        return dest


register(WikimediaCommonsVideoAdapter())
