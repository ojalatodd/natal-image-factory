# Natal Image Factory

Turn an article + voiceover into a packaged set of public-domain **stills and video b-roll**, segmented and timestamped for any video editor.

See the full design in [`Documentation/`](./Documentation):
- [Design Overview](./Documentation/Design-Overview.md) (client-facing)
- [DigitalOcean Cost Analysis](./Documentation/DigitalOcean-Cost-Analysis.md)
- [Technical Implementation Plan](./Documentation/Technical-Implementation-Plan.md)

---

## Architecture (local = production parity)

Containerized via Docker Compose — the same stack runs on local Docker Desktop and on a DigitalOcean Droplet.

| Service | Tech | Port (local) |
|---|---|---|
| `caddy` | Reverse proxy + TLS, serves SPA, proxies `/api` | 80 / 443 |
| `frontend` | React + Vite + Tailwind (built, served by Caddy in prod) | 5173 (dev) |
| `api` | FastAPI + Uvicorn | 8000 |
| `worker` | Celery (+ ffmpeg) pipeline | — |
| `redis` | Celery broker + progress pub/sub | 6379 |
| `minio` | Local S3 (stands in for DO Spaces) | 9000 / 9001 |
| DB | SQLite on a Docker volume (→ managed PostgreSQL in prod) | — |

---

## Quick start (local, Docker Desktop)

```bash
cp .env.example .env
# edit .env: set OPENAI_API_KEY and SECRET_KEY at minimum

docker compose up --build
```

- App:        http://localhost
- API docs:   http://localhost/api/docs
- MinIO UI:   http://localhost:9001  (minioadmin / minioadmin)

### Frontend dev mode (hot reload, optional)
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to the api container
```

---

## Deployment to DigitalOcean

The same Compose stack deploys to a Droplet. Differences are isolated in `docker-compose.prod.yml`:

- **Storage:** swap MinIO for **DO Spaces** — set `SPACES_*` to your Spaces creds/endpoint, drop the `minio` service.
- **Database:** keep SQLite on a volume, or set `DATABASE_URL=postgresql://...` for a managed cluster.
- **TLS:** Caddy auto-provisions Let's Encrypt certs for the real domain.

```bash
# on the Droplet
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

See [Technical-Implementation-Plan.md §10](./Documentation/Technical-Implementation-Plan.md) for the full deployment runbook.

---

## Repo layout

```
backend/    FastAPI app, Celery worker, pipeline stages + source adapters
frontend/   React SPA (upload, settings, review, download)
Caddyfile   reverse proxy config
docker-compose.yml          local stack (Docker Desktop)
docker-compose.prod.yml     DigitalOcean overrides
Documentation/              design + planning docs
```

## Status

Phase 0 (scaffolding) — in progress. Pipeline stages are stubbed and wired; AI/adapter logic lands in Phases 1–4 per the implementation plan.
