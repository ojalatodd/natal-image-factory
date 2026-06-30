"""Regression tests asserting source adapters send User-Agent header.

Uses httpx MockTransport to intercept requests without making real API calls.
Tests both search() and fetch() paths for all 5 source adapters.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BOOTSTRAP_USER_EMAIL", "")
os.environ.setdefault("BOOTSTRAP_USER_PASSWORD", "")

from pathlib import Path

import httpx
import pytest

from app.pipeline.adapters.base import USER_AGENT, HEADERS


def _make_mock_transport(captured_headers: dict, response_json: dict | None = None, response_bytes: bytes = b"fake-image"):
    """Create a MockTransport that captures headers and returns a canned response."""

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers["User-Agent"] = request.headers.get("User-Agent", "")
        captured_headers["url"] = str(request.url)
        if response_json is not None:
            return httpx.Response(200, json=response_json)
        return httpx.Response(200, content=response_bytes)

    return httpx.MockTransport(handler)


@pytest.fixture
def captured():
    return {}


# ---- Wikimedia Commons ----
def test_wikimedia_search_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import wikimedia

    transport = _make_mock_transport(captured, response_json={
        "query": {"search": []}
    })
    monkeypatch.setattr(wikimedia, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    adapter = wikimedia.WikimediaCommonsAdapter()
    asyncio.run(adapter.search("test", style="", min_duration_s=None, limit=5))
    assert captured["User-Agent"] == USER_AGENT


def test_wikimedia_fetch_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import wikimedia
    from app.pipeline.adapters.base import CandidateAsset

    transport = _make_mock_transport(captured)
    monkeypatch.setattr(wikimedia, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    import tempfile
    adapter = wikimedia.WikimediaCommonsAdapter()
    asset = CandidateAsset(
        source_name="Wikimedia Commons",
        media_type="still",
        source_url="https://example.com",
        download_url="https://example.com/image.jpg",
    )
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        dest = Path(tmp.name)
    asyncio.run(adapter.fetch(asset, dest))
    assert captured["User-Agent"] == USER_AGENT
    dest.unlink(missing_ok=True)


# ---- Library of Congress ----
def test_loc_search_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import loc

    transport = _make_mock_transport(captured, response_json={"results": []})
    monkeypatch.setattr(loc, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    adapter = loc.LibraryOfCongressAdapter()
    asyncio.run(adapter.search("test", style="", min_duration_s=None, limit=5))
    assert captured["User-Agent"] == USER_AGENT


def test_loc_fetch_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import loc
    from app.pipeline.adapters.base import CandidateAsset

    transport = _make_mock_transport(captured)
    monkeypatch.setattr(loc, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    import tempfile
    adapter = loc.LibraryOfCongressAdapter()
    asset = CandidateAsset(
        source_name="Library of Congress",
        media_type="still",
        source_url="https://example.com",
        download_url="https://example.com/image.jpg",
    )
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        dest = Path(tmp.name)
    asyncio.run(adapter.fetch(asset, dest))
    assert captured["User-Agent"] == USER_AGENT
    dest.unlink(missing_ok=True)


# ---- Internet Archive ----
def test_internet_archive_search_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import internet_archive

    transport = _make_mock_transport(captured, response_json={"response": {"docs": []}})
    monkeypatch.setattr(internet_archive, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    adapter = internet_archive.InternetArchiveAdapter()
    asyncio.run(adapter.search("test", style="", min_duration_s=None, limit=5))
    assert captured["User-Agent"] == USER_AGENT


def test_internet_archive_fetch_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import internet_archive
    from app.pipeline.adapters.base import CandidateAsset

    transport = _make_mock_transport(captured)
    monkeypatch.setattr(internet_archive, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    import tempfile
    adapter = internet_archive.InternetArchiveAdapter()
    asset = CandidateAsset(
        source_name="Internet Archive",
        media_type="still",
        source_url="https://example.com",
        download_url="https://example.com/image.jpg",
    )
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        dest = Path(tmp.name)
    asyncio.run(adapter.fetch(asset, dest))
    assert captured["User-Agent"] == USER_AGENT
    dest.unlink(missing_ok=True)


# ---- Wikimedia Commons Video ----
def test_wikimedia_video_search_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import wikimedia_video

    transport = _make_mock_transport(captured, response_json={
        "query": {"search": []}
    })
    monkeypatch.setattr(wikimedia_video, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    adapter = wikimedia_video.WikimediaCommonsVideoAdapter()
    asyncio.run(adapter.search("test", style="", min_duration_s=None, limit=5))
    assert captured["User-Agent"] == USER_AGENT


def test_wikimedia_video_fetch_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import wikimedia_video
    from app.pipeline.adapters.base import CandidateAsset

    transport = _make_mock_transport(captured)
    monkeypatch.setattr(wikimedia_video, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    import tempfile
    adapter = wikimedia_video.WikimediaCommonsVideoAdapter()
    asset = CandidateAsset(
        source_name="Wikimedia Commons Video",
        media_type="video",
        source_url="https://example.com",
        download_url="https://example.com/video.ogv",
    )
    with tempfile.NamedTemporaryFile(suffix=".ogv", delete=False) as tmp:
        dest = Path(tmp.name)
    asyncio.run(adapter.fetch(asset, dest))
    assert captured["User-Agent"] == USER_AGENT
    dest.unlink(missing_ok=True)


# ---- Internet Archive Video ----
def test_internet_archive_video_search_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import internet_archive_video

    transport = _make_mock_transport(captured, response_json={"response": {"docs": []}})
    monkeypatch.setattr(internet_archive_video, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    adapter = internet_archive_video.InternetArchiveVideoAdapter()
    asyncio.run(adapter.search("test", style="", min_duration_s=None, limit=5))
    assert captured["User-Agent"] == USER_AGENT


def test_internet_archive_video_fetch_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import internet_archive_video
    from app.pipeline.adapters.base import CandidateAsset

    # IA fetch does a metadata API call then a file download — mock both
    call_count = {"n": 0}
    def handler(request: httpx.Request) -> httpx.Response:
        captured["User-Agent"] = request.headers.get("User-Agent", "")
        call_count["n"] += 1
        if "metadata" in str(request.url):
            return httpx.Response(200, json={"files": [{"name": "video.mp4"}]})
        return httpx.Response(200, content=b"fake-video")

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(internet_archive_video, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    import tempfile
    adapter = internet_archive_video.InternetArchiveVideoAdapter()
    asset = CandidateAsset(
        source_name="Internet Archive Video",
        media_type="video",
        source_url="https://archive.org/details/test",
        download_url=None,
        extra={"identifier": "test"},
    )
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        dest = Path(tmp.name)
    asyncio.run(adapter.fetch(asset, dest))
    assert captured["User-Agent"] == USER_AGENT
    dest.unlink(missing_ok=True)


# ---- The Met ----
def test_met_search_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import met

    transport = _make_mock_transport(captured, response_json={"objectIDs": []})
    monkeypatch.setattr(met, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    adapter = met.MetMuseumAdapter()
    asyncio.run(adapter.search("test", style="", min_duration_s=None, limit=5))
    assert captured["User-Agent"] == USER_AGENT


def test_met_fetch_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import met
    from app.pipeline.adapters.base import CandidateAsset

    transport = _make_mock_transport(captured)
    monkeypatch.setattr(met, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    import tempfile
    adapter = met.MetMuseumAdapter()
    asset = CandidateAsset(
        source_name="The Met",
        media_type="still",
        source_url="https://example.com",
        download_url="https://example.com/image.jpg",
    )
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        dest = Path(tmp.name)
    asyncio.run(adapter.fetch(asset, dest))
    assert captured["User-Agent"] == USER_AGENT
    dest.unlink(missing_ok=True)


# ---- Smithsonian ----
def test_smithsonian_search_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import smithsonian

    transport = _make_mock_transport(captured, response_json={"response": {"rows": []}})
    monkeypatch.setattr(smithsonian, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    adapter = smithsonian.SmithsonianAdapter()
    asyncio.run(adapter.search("test", style="", min_duration_s=None, limit=5))
    assert captured["User-Agent"] == USER_AGENT


def test_smithsonian_fetch_sends_user_agent(captured, monkeypatch):
    from app.pipeline.adapters import smithsonian
    from app.pipeline.adapters.base import CandidateAsset

    transport = _make_mock_transport(captured)
    monkeypatch.setattr(smithsonian, "http_client", lambda **kw: httpx.AsyncClient(transport=transport, headers=HEADERS, **{k: v for k, v in kw.items() if k != "headers"}))

    import asyncio
    import tempfile
    adapter = smithsonian.SmithsonianAdapter()
    asset = CandidateAsset(
        source_name="Smithsonian Open Access",
        media_type="still",
        source_url="https://example.com",
        download_url="https://example.com/image.jpg",
    )
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        dest = Path(tmp.name)
    asyncio.run(adapter.fetch(asset, dest))
    assert captured["User-Agent"] == USER_AGENT
    dest.unlink(missing_ok=True)
