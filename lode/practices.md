# Practices & Patterns

Patterns, conventions, and constraints that matter when changing this codebase.

## Backend

- **Python 3.12**, FastAPI, SQLAlchemy 2.0 (typed Mapped columns), Pydantic v2, Celery, Redis.
- All config via `pydantic-settings` in `backend/app/config.py` — never hardcode secrets; use `.env` (see `.env.example`).
- SQLAlchemy models use `Mapped[T]` / `mapped_column()` typed style. Enums are `str, enum.Enum` subclasses stored as `Enum` columns.
- Routers are thin: validate input with Pydantic schemas, delegate business logic to services/pipeline, return Pydantic response models.
- Auth is JWT-based (`python-jose`). Token in `Authorization: Bearer` header. `get_current_user` dependency in `backend/app/deps.py`.
- Password hashing: `passlib[bcrypt]==1.7.4` with `bcrypt==4.0.1` pinned (newer bcrypt breaks passlib).
- Celery task `run_pipeline` in `backend/app/tasks.py` orchestrates the six stages. Each stage is independently testable.
- Progress updates: `backend/app/progress.py` publishes to Redis pub/sub and updates the `Job` table. Frontend subscribes via WebSocket.
- Storage: `backend/app/storage.py` wraps boto3 for S3-compatible operations. Works with MinIO (local) and DO Spaces (prod).

## Frontend

- **React 18 + Vite + TypeScript + TailwindCSS**. No shadcn/ui components installed yet (listed in dependencies).
- API calls via Axios instance in `frontend/src/api.ts` with JWT interceptor.
- State management: `@tanstack/react-query` for server state, `zustand` for client state (not yet used).
- Routing: `react-router-dom` with auth guard in `App.tsx`.
- Build: `vite build` only (no `tsc -b` — removed to avoid blocking Docker builds on type errors).

## Infrastructure

- **Caddy** serves the SPA and reverse-proxies `/api/*` to the FastAPI backend. Auto-TLS in production.
- Docker Compose: `docker-compose.yml` for local dev, `docker-compose.prod.yml` overrides for DigitalOcean.
- Frontend Dockerfile build context is the **repo root** (not `frontend/`), because it copies `Caddyfile` from root.
- SQLite at `/data/app.db` in local dev. Volume `db_data` shared between `api` and `worker` containers.
- MinIO for local S3 emulation. Console at `:9001`, API at `:9000`.

## Git

- Default branch: `main`. Remote: `github.com/ojalatodd/natal-image-factory`.
- **Branching strategy (mandatory)**: ALWAYS create a new branch from `main` before starting any new phase, stage, or feature of development. Never commit feature work directly to `main`. Create the branch as the very first step, before writing any code. Use a rational, descriptive name (e.g., `phase1-whisper-transcription`, `feat-source-adapters`, `fix-celery-progress`). Merge back to `main` via PR or fast-forward after review.
- Branch naming convention: `phase{n}-{feature}` for phase work, `feat-{feature}` for standalone features, `fix-{issue}` for bug fixes.
- **Pre-commit checklist**: Before committing, ensure `.env` is never staged. After committing, push the branch to origin.
- `.gitattributes` normalizes line endings to LF.
- `lode/tmp/` is git-ignored (session scraps only).

## Lode Coding

- The `lode/` directory is the AI's persistent memory. It describes **current state**, not changelog history.
- Every lode file covers exactly one topic, stays under 250 lines, and uses Mermaid diagrams (not SVG).
- After code changes, update the corresponding lode file before moving to the next task.
- Session handovers go in `lode/tmp/` (git-ignored).
