"""Application configuration, loaded from environment variables / .env.

Everything has a default so the app boots with an empty environment
(SQLite + local storage + no Telegram bot).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- General ----
    app_name: str = "AutoTracker"
    environment: str = "development"
    log_level: str = "INFO"
    # Set by the Vercel entrypoint (api/index.py). Disables anything that needs
    # a long-lived process: the alert scheduler and the Telegram polling thread.
    serverless: bool = False
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ---- Auth ----
    single_user: bool = True
    single_user_email: str = "owner@autotracker.local"
    single_user_name: str = "Owner"
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 10080
    algorithm: str = "HS256"

    # ---- Database ----
    database_url: str = "sqlite:///./data/autotracker.db"

    # ---- Storage ----
    storage_backend: str = "minio"  # minio | local
    s3_endpoint: str = "minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "autotracker"
    s3_secure: bool = False
    s3_region: str = "us-east-1"
    local_storage_dir: str = "./data/storage"

    # ---- OCR ----
    ocr_enabled: bool = True
    tesseract_cmd: str = "tesseract"
    ocr_languages: str = "eng"

    # ---- Telegram ----
    telegram_bot_token: str = ""
    telegram_autodelete_seconds: int = 300
    public_base_url: str = "http://localhost:8000"

    # ---- Scheduler / alerts ----
    scheduler_enabled: bool = True
    alert_lead_days: str = "30,14,7,1"
    alert_sweep_hour: int = 8

    @field_validator("cors_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def alert_lead_day_list(self) -> list[int]:
        out: list[int] = []
        for part in self.alert_lead_days.split(","):
            part = part.strip()
            if part.isdigit():
                out.append(int(part))
        return sorted(set(out), reverse=True)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token.strip())

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
