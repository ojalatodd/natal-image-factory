# Frontend Summary

React 18 + Vite + TypeScript + TailwindCSS single-page application.

**Entry point:** `frontend/src/main.tsx` — sets up React Query and React Router.

**Pages:**
- `Login.tsx` — Email/password form, calls `/api/auth/login`, stores JWT in localStorage.
- `Dashboard.tsx` — Lists projects, creates new projects, sign-out.
- `ProjectView.tsx` — Project detail: upload text/audio (both required for generate), configure settings (media mix, visual style, AI toggles), trigger pipeline, view live progress via WebSocket, segment review UI with asset thumbnails and click-to-swap, download ZIP (presigned URL from API).
- `AiSettings.tsx` — Global AI provider/model configuration (provider, text model, vision model, image model).

**Segment Review UI (Phase 1):**
- Fetches segments via `listSegments(projectId)` when project status is `review` or `complete`.
- Each segment card shows: index, theme label, timestamp range, summary, chosen asset indicator.
- Asset thumbnails displayed in horizontal scroll; chosen asset has blue border + check icon.
- Click any thumbnail to swap the chosen asset via `swapAsset(segmentId, assetId)`.
- Download button fetches presigned URL via `getDownloadUrl(projectId)`.

**API layer:** `frontend/src/api.ts` — Axios instance with JWT interceptor. Exports typed interfaces (`Project`, `Segment`, `Asset`) and functions: `login`, `listProjects`, `createProject`, `getProject`, `listSegments`, `swapAsset`, `getDownloadUrl`. Base URL proxied via Vite dev server to `http://localhost:8000`.

**Routing:** `App.tsx` — Auth guard redirects to `/login` if no JWT in localStorage. Routes: `/login`, `/` (Dashboard), `/projects/:id` (ProjectView).

**Build:** `vite build` produces static assets in `dist/`. Served by Caddy in Docker.

See: [architecture.md](architecture.md)
