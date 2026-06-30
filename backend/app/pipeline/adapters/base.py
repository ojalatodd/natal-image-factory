"""Pluggable source adapter interface.

Every public-domain source (stills or video) implements this Protocol so the
pipeline can query sources uniformly. Concrete adapters (Library of Congress,
Wikimedia, Internet Archive, NARA, NASA, Pexels, ...) land in Phases 1 & 3.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

import httpx

MediaTypeStr = Literal["still", "video"]

# Descriptive User-Agent required by several public APIs (notably Wikimedia
# Commons, which returns 403 without one). See:
# https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = (
    "NatalImageFactory/1.0 (https://github.com/ojalatodd/natal-image-factory; "
    "public-domain media aggregator)"
)
HEADERS = {"User-Agent": USER_AGENT}


def http_client(*, timeout: int = 30, follow_redirects: bool = False) -> httpx.AsyncClient:
    """Return an AsyncClient pre-configured with the required User-Agent header.

    Using this factory instead of ``httpx.AsyncClient(..., headers=HEADERS)``
    makes it impossible to forget the User-Agent header in future adapters.
    """
    return httpx.AsyncClient(timeout=timeout, follow_redirects=follow_redirects, headers=HEADERS)


@dataclass
class CandidateAsset:
    source_name: str
    media_type: MediaTypeStr
    source_url: str
    thumbnail_url: str | None = None
    download_url: str | None = None
    license: str | None = None
    attribution: str | None = None
    title: str | None = None
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None
    extra: dict = field(default_factory=dict)


@runtime_checkable
class SourceAdapter(Protocol):
    name: str
    media_type: MediaTypeStr
    license_default: str

    async def search(
        self,
        query: str,
        *,
        style: str,
        min_duration_s: float | None,
        limit: int,
    ) -> list[CandidateAsset]:
        """Return candidate assets matching the query. Metadata + thumbnail only."""
        ...

    async def fetch(self, asset: CandidateAsset, dest: Path) -> Path:
        """Download the full asset to dest; return the local path."""
        ...


# Registry populated by concrete adapter modules as they are implemented.
# Keyed by (name, media_type) so same-named still/video adapters don't collide.
_REGISTRY: dict[tuple[str, MediaTypeStr], SourceAdapter] = {}


def register(adapter: SourceAdapter) -> SourceAdapter:
    _REGISTRY[(adapter.name, adapter.media_type)] = adapter
    return adapter


def get_adapters(media_type: MediaTypeStr | None = None) -> list[SourceAdapter]:
    # Ensure adapter modules are imported so they register themselves
    if not _REGISTRY:
        from app.pipeline import adapters as _adapters  # noqa: F401
    adapters = list(_REGISTRY.values())
    if media_type:
        adapters = [a for a in adapters if a.media_type == media_type]
    return adapters
