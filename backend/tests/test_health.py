"""Smoke tests. Uses an in-memory SQLite DB and the FastAPI TestClient."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BOOTSTRAP_USER_EMAIL", "")
os.environ.setdefault("BOOTSTRAP_USER_PASSWORD", "")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_health():
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_auth_required():
    with TestClient(app) as client:
        resp = client.get("/api/projects")
        assert resp.status_code == 401
