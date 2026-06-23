# Docker Compose (Local Dev)

## Configuration

`docker-compose.yml` defines the local development stack:

- **web**: Caddy serving the built SPA and reverse-proxying `/api/*` to the `api` service. Build context is the repo root (`.`), Dockerfile at `frontend/Dockerfile`. `SITE_ADDRESS` set to `:80`.
- **api**: FastAPI app built from `backend/Dockerfile`. Loads `.env` file. Exposes port 8000 for local frontend dev (`npm run dev`). Depends on `redis` and `minio`. Mounts `db_data` volume at `/data`.
- **worker**: Same build as `api` but runs Celery worker command. Shares `db_data` volume. Depends on `redis` and `minio`.
- **redis**: `redis:7-alpine` — no port exposed (internal only).
- **minio**: MinIO server with console on `:9001`. Credentials from `SPACES_KEY`/`SPACES_SECRET` env vars (default `minioadmin`). Mounts `minio_data` volume.

## Key Decisions

- **Frontend Dockerfile context is repo root** because it needs to copy `Caddyfile` from the root directory.
- **API port 8000 is exposed** to support local `npm run dev` without Docker for the frontend. The Vite dev proxy targets `http://localhost:8000`.
- **SQLite volume is shared** between `api` and `worker` so both can read/write the same database.
- **No `tsc -b` in frontend build** — removed to prevent Docker build failures from TypeScript errors blocking the production build.

## Production Override

`docker-compose.prod.yml` overrides for DigitalOcean deployment:
- `web` ports change to `80:80` and `443:443` (Caddy auto-TLS)
- `api` environment sets `APP_ENV: production`
- `minio` service is disabled (`profiles: ["disabled"]`)
- Storage switches to DO Spaces via env vars
