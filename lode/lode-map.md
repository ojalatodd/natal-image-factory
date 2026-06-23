# Lode Map

Hierarchical index of all lode files. **Read this first** before exploring the codebase.

## Top-Level

- [summary.md](summary.md) — One-paragraph project snapshot
- [terminology.md](terminology.md) — Domain language glossary
- [practices.md](practices.md) — Patterns, conventions, and constraints

## Plans

- [plans/roadmap.md](plans/roadmap.md) — Phase roadmap and implementation plan

## Backend

- [backend/summary.md](backend/summary.md) — Backend service overview
- [backend/architecture.md](backend/architecture.md) — FastAPI app structure, routers, middleware
- [backend/models.md](backend/models.md) — SQLAlchemy ORM models and enums
- [backend/auth.md](backend/auth.md) — JWT authentication, password hashing, bootstrap user
- [backend/storage.md](backend/storage.md) — S3-compatible object storage (MinIO/Spaces)
- [backend/celery.md](backend/celery.md) — Celery task orchestration and progress tracking

## Frontend

- [frontend/summary.md](frontend/summary.md) — Frontend SPA overview
- [frontend/architecture.md](frontend/architecture.md) — React app structure, routing, API layer

## Pipeline

- [pipeline/summary.md](pipeline/summary.md) — Pipeline overview and data flow
- [pipeline/stages.md](pipeline/stages.md) — The six pipeline stages (current stubs + future implementation)
- [pipeline/adapters.md](pipeline/adapters.md) — Source adapter protocol and pluggable media sources

## Infrastructure

- [infrastructure/summary.md](infrastructure/summary.md) — Docker, Caddy, deployment overview
- [infrastructure/docker-compose.md](infrastructure/docker-compose.md) — Local dev stack configuration
- [infrastructure/deployment.md](infrastructure/deployment.md) — DigitalOcean production deployment
