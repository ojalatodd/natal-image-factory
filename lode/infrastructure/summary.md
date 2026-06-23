# Infrastructure Summary

## Local Development Stack

```mermaid
graph TD
    Browser --> Caddy[Caddy :80]
    Caddy -->|static files| SPA[React SPA]
    Caddy -->|/api/* proxy| API[FastAPI :8000]
    Caddy -->|/ws/* proxy| API
    API --> Redis[Redis :6379]
    API --> MinIO[MinIO :9000]
    Worker[Celery Worker] --> Redis
    Worker --> MinIO
    Worker --> SQLite[(SQLite /data/app.db)]
    API --> SQLite
```

## Services (docker-compose.yml)

| Service | Image/Build | Port | Purpose |
|---------|------------|------|---------|
| `web` | Built from `frontend/Dockerfile` | 80 | Caddy serving SPA + reverse proxy |
| `api` | Built from `backend/Dockerfile` | 8000 | FastAPI application |
| `worker` | Built from `backend/Dockerfile` | — | Celery worker |
| `redis` | `redis:7-alpine` | — | Message broker + pub/sub |
| `minio` | `minio/minio:latest` | 9000, 9001 | S3-compatible storage |

## Volumes

- `db_data` — SQLite database, shared between `api` and `worker`
- `minio_data` — MinIO object storage

See: [docker-compose.md](docker-compose.md), [deployment.md](deployment.md)
