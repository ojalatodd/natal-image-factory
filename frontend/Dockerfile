# NOTE: build context is the repo ROOT (set in docker-compose.yml) so we can
# also copy the shared Caddyfile. Paths below are relative to the repo root.

# ---- Stage 1: build the SPA ----
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# ---- Stage 2: serve via Caddy (also reverse-proxies /api) ----
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
