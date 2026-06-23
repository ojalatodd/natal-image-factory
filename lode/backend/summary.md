# Backend Summary

The backend is a Python 3.12 FastAPI application served by Uvicorn, with Celery for async pipeline processing and Redis as broker/pub-sub.

**Entry point:** `backend/app/main.py` — creates the FastAPI app with `root_path="/api"`, includes routers, configures CORS, runs startup tasks (DB init, bucket ensure, bootstrap user), and exposes a WebSocket for progress streaming.

**Key modules:**
- `config.py` — Pydantic-settings loading from `.env`
- `database.py` — SQLAlchemy engine/session, `init_db()`
- `models.py` — ORM models: User, Project, Segment, Asset, SourceAdapterConfig, Job
- `schemas.py` — Pydantic request/response schemas
- `security.py` — bcrypt password hashing, JWT create/decode
- `deps.py` — FastAPI dependencies (get_db, get_current_user)
- `storage.py` — boto3 S3-compatible client (MinIO/Spaces)
- `celery_app.py` — Celery app with Redis broker
- `progress.py` — Job progress persistence + Redis pub/sub
- `tasks.py` — `run_pipeline` Celery task
- `pipeline/stages.py` — Six pipeline stage functions
- `pipeline/adapters/base.py` — SourceAdapter protocol
- `pipeline/media.py` — ffmpeg/ffprobe helpers (stubs)

**Routers:**
- `auth.py` — login, get current user
- `projects.py` — CRUD, generate (trigger pipeline), download
- `uploads.py` — upload text/audio files to Spaces
- `segments.py` — list segments, swap asset
- `sources.py` — list/update source adapter configs

See: [architecture.md](architecture.md), [models.md](models.md), [auth.md](auth.md), [storage.md](storage.md), [celery.md](celery.md)
