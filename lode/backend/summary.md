# Backend Summary

The backend is a Python 3.12 FastAPI application served by Uvicorn, with Celery for async pipeline processing and Redis as broker/pub-sub.

**Entry point:** `backend/app/main.py` — creates the FastAPI app with `root_path="/api"`, includes routers, configures CORS, runs startup tasks (DB init, bucket ensure, bootstrap user), and exposes a WebSocket for progress streaming.

**Key modules:**
- `config.py` — Pydantic-settings loading from `.env`
- `database.py` — SQLAlchemy engine/session, `init_db()`
- `models.py` — ORM models: User, Project, Segment, Asset, SourceAdapterConfig, AiSettings, Job
- `schemas.py` — Pydantic request/response schemas
- `security.py` — bcrypt password hashing, JWT create/decode
- `deps.py` — FastAPI dependencies (get_db, get_current_user)
- `storage.py` — boto3 S3-compatible client (MinIO/Spaces)
- `celery_app.py` — Celery app with Redis broker
- `progress.py` — Job progress persistence + Redis pub/sub
- `tasks.py` — `run_pipeline` Celery task
- `ai.py` — Multi-provider AI helpers (OpenAI/Anthropic/Gemini/DeepSeek) for segmentation/ranking, OpenAI Vision and DALL-E
- `pipeline/stages.py` — Six pipeline stage functions (Phase 1 implemented)
- `pipeline/adapters/base.py` — SourceAdapter protocol + registry
- `pipeline/adapters/wikimedia.py` — Wikimedia Commons adapter
- `pipeline/adapters/loc.py` — Library of Congress adapter
- `pipeline/adapters/internet_archive.py` — Internet Archive adapter
- `pipeline/image_utils.py` — Pillow image normalization (resize, convert, thumbnail)
- `pipeline/media.py` — ffmpeg/ffprobe helpers (stubs for Phase 3)

**Routers:**
- `auth.py` — login, get current user
- `projects.py` — CRUD, generate (requires text + audio upload), download (review or complete status)
- `uploads.py` — upload text/audio files to Spaces
- `segments.py` — list segments, swap asset
- `sources.py` — list/update source adapter configs
- `ai_settings.py` — get/update global AI provider/model configuration

See: [architecture.md](architecture.md), [models.md](models.md), [auth.md](auth.md), [storage.md](storage.md), [celery.md](celery.md)
