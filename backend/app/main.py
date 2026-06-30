import asyncio
import contextlib
import json
import logging

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import User
from app.progress import channel
from app.routers import ai_settings, auth, projects, segments, sources, uploads, visual_styles
from app.security import hash_password
from app.storage import ensure_bucket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("natal")

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)

app = FastAPI(title="Natal Image Factory API", version="0.1.0", root_path="/api")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(uploads.router)
app.include_router(segments.router)
app.include_router(sources.router)
app.include_router(ai_settings.router)
app.include_router(visual_styles.router)


def _bootstrap_user() -> None:
    if not (settings.bootstrap_user_email and settings.bootstrap_user_password):
        return
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(
                User(
                    email=settings.bootstrap_user_email,
                    password_hash=hash_password(settings.bootstrap_user_password),
                )
            )
            db.commit()
            logger.info("Bootstrapped initial user %s", settings.bootstrap_user_email)
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with contextlib.suppress(Exception):
        ensure_bucket()
    _bootstrap_user()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


@app.websocket("/projects/{project_id}/progress")
async def progress_ws(websocket: WebSocket, project_id: int) -> None:
    await websocket.accept()
    r = aioredis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe(channel(project_id))
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                data = msg["data"]
                await websocket.send_text(data.decode() if isinstance(data, bytes) else json.dumps(data))
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel(project_id))
        await r.aclose()
