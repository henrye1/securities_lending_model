from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    # Supabase is the target database. When the URL/key are absent the app runs
    # on a local JSON-file store so the suite works out of the box in dev.
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # 8003/5176: the insurance (8000/5173), bank (8001/5174) and finance company
    # (8002/5175) siblings keep their defaults, so all suite apps run side by side.
    backend_port: int = 8003
    # NoDecode: accept plain CSV in .env instead of requiring a JSON list
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5176"]
    )
    dev_store_path: str = "./dev_store.json"
    # Production: directory of the built frontend (frontend/dist). When set and
    # present, the backend serves the SPA itself so one Render service hosts
    # both API and UI (same origin, no CORS).
    frontend_dist: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def use_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
