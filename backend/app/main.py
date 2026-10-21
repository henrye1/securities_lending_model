from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Securities Lending Model", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.use_supabase:
        from app.repositories.supabase_store import SupabaseStore

        app.state.store = SupabaseStore()
    else:
        from app.repositories.store import MemoryStore

        logging.getLogger(__name__).warning(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set - using local JSON store %s "
            "(data is lost on redeploy when hosted)",
            settings.dev_store_path,
        )
        app.state.store = MemoryStore(persist_path=settings.dev_store_path)

    app.include_router(router)
    _mount_frontend(app, settings.frontend_dist)
    return app


def _mount_frontend(app: FastAPI, dist: str) -> None:
    """Serve the built SPA (vite `dist/`) with history-API fallback."""
    if not dist:
        return
    root = Path(dist).resolve()
    index = root / "index.html"
    if not index.is_file():
        logging.getLogger(__name__).warning("FRONTEND_DIST=%s has no index.html - not serving UI", root)
        return
    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = root / path
        if path and candidate.is_file() and candidate.resolve().is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=get_settings().backend_port, reload=True)
