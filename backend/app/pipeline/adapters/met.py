"""The Met (Metropolitan Museum of Art) source adapter — Open Access images.

Uses The Met's public Open Access API to search for public-domain artworks.
No API key required.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.pipeline.adapters.base import HEADERS, CandidateAsset, register

logger = logging.getLogger("natal")

MET_API = "https://collectionapi.metmuseum.org/public/collection/v1"


class MetMuseumAdapter:
    name = "The Met"
    media_type = "still"  # type: ignore[assignment]
    license_default = "Open Access (CC0)"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def search(
        self,
        query: str,
        *,
        style: str = "",
        min_duration_s: float | None = None,
        limit: int = 10,
    ) -> list[CandidateAsset]:
        # Search for objects
        params = {"q": query, "hasImages": "true", "isPublicDomain": "true"}
        async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
            resp = await client.get(f"{MET_API}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        object_ids = data.get("objectIDs", []) or []
        if not object_ids:
            return []

        async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
            async def _fetch_object(oid: int) -> CandidateAsset | None:
                try:
                    obj_resp = await client.get(f"{MET_API}/objects/{oid}")
                    obj_resp.raise_for_status()
                    obj = obj_resp.json()

                    if not obj.get("isPublicDomain"):
                        return None

                    primary_image = obj.get("primaryImage") or obj.get("primaryImageSmall")
                    if not primary_image:
                        return None

                    return CandidateAsset(
                        source_name=self.name,
                        media_type="still",
                        source_url=obj.get("objectURL", f"https://www.metmuseum.org/art/collection/search/{oid}"),
                        thumbnail_url=obj.get("primaryImageSmall") or primary_image,
                        download_url=primary_image,
                        license=self.license_default,
                        attribution=f"The Met: {obj.get('title', '')} — {obj.get('artistDisplayName', 'Unknown')}",
                        title=obj.get("title", ""),
                    )
                except Exception as exc:
                    logger.debug("Met object %d failed: %s", oid, exc)
                    return None

            results = await asyncio.gather(*[_fetch_object(oid) for oid in object_ids[:limit]])

        candidates = [c for c in results if c is not None]
        return candidates[:limit]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def fetch(self, asset: CandidateAsset, dest: Path) -> Path:
        url = asset.download_url or asset.thumbnail_url
        if not url:
            raise ValueError(f"No download URL for asset from {self.name}")
        async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers=HEADERS) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
        return dest


register(MetMuseumAdapter())
