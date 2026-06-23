# Phase Roadmap

## Phase 0 — Scaffold (COMPLETE)

- Git repo, .gitignore, .env.example, README
- Backend: FastAPI app, config, database, models, auth, storage, Celery
- Backend routers: auth, projects, uploads, segments, sources
- Pipeline stage stubs (6 stages, safe placeholders)
- Frontend: React + Vite + Tailwind + Login/Dashboard/ProjectView
- Docker: backend/frontend Dockerfiles, Caddyfile, docker-compose (local + prod)
- Verified: full stack builds and runs in Docker Desktop
- Pushed to `github.com/ojalatodd/natal-image-factory` main branch

## Phase 1 — Core Still Image Pipeline

- **Stage 1 (Transcribe):** Integrate OpenAI Whisper API on `source_audio_key`, return word-level timeline.
- **Stage 2 (Segment):** GPT-4o over article text + transcript → thematic segments with timestamps, theme labels, summaries, and search queries.
- **Stage 3 (Search - Stills):** Implement source adapters for Wikimedia Commons, Flickr Commons, Internet Archive. Query per segment search_query + visual_style.
- **Stage 4 (Rank):** GPT-4o Vision scores candidate thumbnails against segment summary. Set `chosen_asset_id`.
- **Stage 5 (Acquire):** Download chosen stills, normalize (resize/format), upload to Spaces.
- **Stage 6 (Package):** Build numbered files + `manifest.txt`, zip, upload to Spaces `output/`.
- Frontend: Wire segment review UI, asset swap, download link.

## Phase 2 — Polish & User Experience

- Source adapter management UI (enable/disable, priority)
- Visual style picker with presets
- AI-generated images toggle (DALL-E / SD)
- Ken Burns motion on stills (ffmpeg pan/zoom)
- Animated maps for geographic segments
- Project history and re-generation

## Phase 3 — Video Pipeline

- Video source adapters (Pexels, Internet Archive video, Wikimedia video)
- `probe_duration`, `trim_and_normalize` via ffprobe/ffmpeg
- Video-specific ranking (motion relevance, content match)
- Media mix enforcement (stills/video/balanced/ai_judgement)
- Video transcoding and format normalization

## Phase 4 — Production Deployment

- DigitalOcean Droplet provisioning
- DO Spaces configuration (replace MinIO)
- Caddy auto-TLS with real domain
- Environment hardening (secrets, CORS, rate limiting)
- SQLite → PostgreSQL migration (if needed)
- Monitoring and logging
