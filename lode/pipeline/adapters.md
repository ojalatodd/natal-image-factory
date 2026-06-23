# Source Adapters

## Protocol

Defined in `backend/app/pipeline/adapters/base.py`:

```python
@dataclass
class CandidateAsset:
    media_type: MediaType          # still or video
    source_name: str               # e.g. "Wikimedia Commons"
    source_url: str                # original URL
    thumbnail_url: str | None
    download_url: str | None
    license: str | None
    attribution: str | None
    width: int | None
    height: int | None
    duration_s: float | None       # video only

class SourceAdapter(Protocol):
    name: str
    media_type: MediaType
    license_default: str

    async def search(self, query: str, *, style: str, min_duration_s: float | None, limit: int) -> list[CandidateAsset]: ...
    async def fetch(self, asset: CandidateAsset, dest: Path) -> Path: ...
```

Adapters register themselves via `register()` at import time. The pipeline imports adapter modules in `stages.py` to trigger registration.

## Implemented Adapters (Phase 1)

### Wikimedia Commons (`adapters/wikimedia.py`)
- **API**: `commons.wikimedia.org/w/api.php` (no key required)
- **Media type**: still
- **Search**: Queries File: namespace, filters out non-image formats (PDF, SVG, OGG, OGV, WebM, MP4). Returns thumbnail (400px) and full-resolution URLs via `Special:FilePath`.
- **Fetch**: Downloads full image via `Special:FilePath` with redirects.
- **Retry**: 3 attempts with exponential backoff (1s-8s).

### Library of Congress (`adapters/loc.py`)
- **API**: `www.loc.gov/search/` (no key required)
- **Media type**: still
- **Search**: Queries photos collection with JSON format. Filters out collections. Uses `image_url` field for thumbnails and downloads.
- **Fetch**: Direct HTTP download with redirects.
- **Retry**: 3 attempts with exponential backoff.

### Internet Archive (`adapters/internet_archive.py`)
- **API**: `archive.org/advancedsearch.php` (no key required)
- **Media type**: still
- **Search**: Queries texts and image media types. Uses `archive.org/services/img/{identifier}` for thumbnails.
- **Fetch**: Direct HTTP download with redirects.
- **Retry**: 3 attempts with exponential backoff.

## Planned Adapters (Phase 2+)

| Adapter | Media Type | API Key | Phase |
|---------|-----------|---------|-------|
| The Met | still | None | 2 |
| Smithsonian Open Access | still | None | 2 |
| Europeana | still | None | 2 |
| NASA Image Library | still | None | 2 |
| NARA (National Archives) | video | None | 3 |
| Pexels | video | Required | 3 |

## User Configuration

Users configure enabled sources and priorities via `PUT /settings/sources`. Configurations are stored in the `SourceAdapterConfig` table per user. The pipeline uses all registered adapters in Phase 1; per-user enable/disable filtering is planned for Phase 2.

## Invariants

- All adapters must implement the `SourceAdapter` protocol.
- Adapters return `CandidateAsset` objects — the pipeline converts these to `Asset` DB records.
- Media mix policy is enforced at the search stage: if `media_mix == stills`, only still adapters are queried; if `video`, only video; if `balanced`, both; if `ai_judgement`, stills only (Phase 1).
