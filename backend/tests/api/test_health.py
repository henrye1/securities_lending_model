from fastapi.testclient import TestClient

from app.main import create_app


def test_health():
    with TestClient(create_app()) as c:
        assert c.get("/api/health").json() == {"status": "ok", "model": "securities-lending-model"}
