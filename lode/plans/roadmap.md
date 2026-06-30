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

## Phase 1 — Core Still Image Pipeline (IMPLEMENTED)

- **Stage 1 (Transcribe):** OpenAI Whisper API integration with word-level timeline. Graceful fallback when no API key.
- **Stage 2 (Segment):** GPT-4o semantic segmentation with theme labels, summaries, and search queries. Graceful fallback.
- **Stage 3 (Search - Stills):** Three source adapters implemented: Wikimedia Commons, Library of Congress, Internet Archive. All use public APIs (no key required).
- **Stage 4 (Rank):** GPT-4o Vision scores candidate thumbnails against segment summary. Graceful fallback to default scores.
- **Stage 5 (Acquire):** Download chosen stills via adapter fetch or httpx, normalize with Pillow (resize/convert to JPEG), upload to Spaces. Thumbnails generated and uploaded.
- **Stage 6 (Package):** ZIP with numbered files (01.jpg, 02.jpg, ...) + manifest.txt with timestamp ranges, source, license, attribution.
- Frontend: Segment review UI with asset thumbnails, click-to-swap, download button for review/complete status.

## Phase 2 — Polish & User Experience (IN PROGRESS)

- Source adapter management UI (enable/disable, priority) — DONE
- Visual style picker with presets — DONE
- AI-generated images toggle (DALL-E 3 fallback) — DONE
- Ken Burns motion on stills (ffmpeg pan/zoom) — DONE
- Animated maps for geographic segments — TODO (Phase 3)
- Project re-generation support — DONE
- Additional source adapters: The Met, Smithsonian Open Access — DONE

## Phase 3 — Video Pipeline (IMPLEMENTED)

- Video source adapters: Pexels, Internet Archive Video, Wikimedia Commons Video — DONE
- `probe_duration`, `trim_and_normalize` via ffprobe/ffmpeg — DONE
- Video-specific ranking: Vision API gives boost to video for action/movement segments — DONE
- Media mix enforcement: stills/video/balanced/ai_judgement with `_enforce_balanced_mix` — DONE
- AI judgement mode: `decide_media_type` asks AI per-segment whether still or video is better — DONE
- Video transcoding and format normalization (H.264 1080p, faststart) — DONE
- Ken Burns motion on stills (ffmpeg zoompan) — DONE
- Video thumbnail extraction — DONE
- Inline video player in segment review UI — DONE
- Video assets in ZIP packaging with manifest entries — DONE

## Phase 4 — Production Deployment

- DigitalOcean Droplet provisioning
- DO Spaces configuration (replace MinIO)
- Caddy auto-TLS with real domain
- Environment hardening: rate limiting — DONE, CORS — DONE, httpOnly cookies — DONE
- Admin dashboard with user management — DONE
- SQLite → PostgreSQL migration (if needed)
- Monitoring and logging
