"""Backend serves the built SPA when FRONTEND_DIST points at a vite dist."""
from fastapi.testclient import TestClient

from app.core import settings as settings_mod
from app.main import create_app


def test_spa_served_with_history_fallback(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>SPA</html>", encoding="utf-8")
    (tmp_path / "assets" / "x.js").write_text("1", encoding="utf-8")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    settings_mod.get_settings.cache_clear()
    try:
        c = TestClient(create_app())
        assert c.get("/").text == "<html>SPA</html>"
        assert c.get("/batches/abc").text == "<html>SPA</html>"
        assert c.get("/assets/x.js").text == "1"
        assert c.get("/api/health").status_code == 200
        assert c.get("/api/nope").status_code == 404
    finally:
        settings_mod.get_settings.cache_clear()
