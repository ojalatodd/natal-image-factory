# Celery & Progress Tracking

## Celery Configuration

`backend/app/celery_app.py` creates a Celery app with Redis as both broker and result backend.

```mermaid
graph TD
    API[FastAPI /projects/{id}/generate] -->|delay| Task[run_pipeline task]
    Task --> Stage1[transcribe]
    Stage1 --> Stage2[segment]
    Stage2 --> Stage3[search_media]
    Stage3 --> Stage4[rank_match]
    Stage4 --> Stage5[acquire_process]
    Stage5 --> Stage6[package]
    Stage6 -->|return zip key| Task
    Task -->|update Project.status| DB
```

- **Broker**: `REDIS_URL` (default `redis://redis:6379/0`)
- **Task module**: `app.tasks` (imported in `celery_app.py` include)
- **Worker command**: `celery -A app.celery_app.celery_app worker --loglevel=info`

## run_pipeline Task

Located in `backend/app/tasks.py`:
1. Loads the Project from DB by ID.
2. Sets `Project.status = processing`.
3. Calls each stage in sequence: `transcribe` → `segment` → `search_media` → `rank_match` → `acquire_process` → `package`.
4. On success: sets `Project.status = complete`, stores output ZIP key.
5. On failure: sets `Project.status = error`, records error in Job table.
6. Each stage receives the DB session and project/segments as needed.

## Progress Tracking

`backend/app/progress.py` provides:
- `publish(project_id, stage, pct, message)` — Updates the `Job` table and publishes to Redis pub/sub channel `progress:{project_id}`.
- `channel(project_id)` — Returns the Redis channel name.

The FastAPI WebSocket at `/api/projects/{project_id}/progress` subscribes to this channel and forwards messages to the connected client in real-time.

## Invariants

- The worker and API containers share the same SQLite database volume (`db_data`).
- Progress messages are JSON with `{"stage": "..., "pct": ..., "message": "..."}`.
- The WebSocket polls Redis pub/sub with a 1-second timeout and 50ms sleep cycle.
