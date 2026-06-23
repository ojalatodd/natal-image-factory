# Frontend Summary

React 18 + Vite + TypeScript + TailwindCSS single-page application.

**Entry point:** `frontend/src/main.tsx` — sets up React Query and React Router.

**Pages:**
- `Login.tsx` — Email/password form, calls `/api/auth/login`, stores JWT in localStorage.
- `Dashboard.tsx` — Lists projects, creates new projects, sign-out.
- `ProjectView.tsx` — Project detail: upload text/audio, configure settings (media mix, visual style, AI toggles), trigger pipeline, view live progress via WebSocket, download ZIP.

**API layer:** `frontend/src/api.ts` — Axios instance with JWT interceptor (adds `Authorization: Bearer` header from localStorage). Base URL proxied via Vite dev server to `http://localhost:8000`.

**Routing:** `App.tsx` — Auth guard redirects to `/login` if no JWT in localStorage. Routes: `/login`, `/` (Dashboard), `/projects/:id` (ProjectView).

**Build:** `vite build` produces static assets in `dist/`. Served by Caddy in Docker.

See: [architecture.md](architecture.md)
