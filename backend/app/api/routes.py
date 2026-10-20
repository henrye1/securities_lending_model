"""API routes - mirrors the suite siblings' endpoint surface."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "model": "securities-lending-model"}
