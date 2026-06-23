# Backend Architecture

## FastAPI App Structure

```mermaid
graph TD
    A[main.py] --> B[CORS Middleware]
    A --> C[Routers]
    A --> D[Startup Events]
    A --> E[Health Endpoint]
    A --> F[WebSocket /progress]
    
    C --> C1[auth.py - /auth/*]
    C --> C2[projects.py - /projects/*]
    C --> C3[uploads.py - /uploads/*]
    C --> C4[segments.py - /projects/{id}/segments/*]
    C --> C5[sources.py - /sources/*]
    
    D --> D1[init_db - create tables]
    D --> D2[ensure_bucket - S3 bucket]
    D --> D3[_bootstrap_user - initial admin]
```

## Request Flow

1. Caddy reverse-proxies `/api/*` to Uvicorn on port 8000.
2. FastAPI app has `root_path="/api"` — all routes are prefixed with `/api` in OpenAPI docs.
3. JWT auth via `Authorization: Bearer` header, validated by `get_current_user` dependency.
4. Router handlers use `Depends(get_db)` for SQLAlchemy sessions and `Depends(get_current_user)` for auth.

## Key Invariants

- The app always runs with `root_path="/api"` — frontend API calls target `/api/*`.
- CORS allows all origins in development, none in production (`settings.is_production`).
- Startup events are synchronous (`@app.on_event("startup")`) — DB init, bucket creation, and bootstrap user all happen before the app accepts requests.
- The WebSocket endpoint at `/projects/{project_id}/progress` subscribes to Redis pub/sub channel `progress:{project_id}` and forwards messages to the client.

## Error Handling

- Current Phase 0: minimal error handling. Router handlers raise `HTTPException` for auth failures and not-found cases.
- Pipeline errors are caught in `tasks.py` and recorded in the `Job` table with `error` field.
- `ensure_bucket()` on startup is wrapped in `contextlib.suppress(Exception)` — storage failures don't block app startup.
