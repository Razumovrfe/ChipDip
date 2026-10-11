from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str
    chipdip_url: str = "https://www.chipdip.by"

    check_interval_minutes: int = 30
    max_search_pages: int = 5

    request_delay_seconds: float = 3.0
    parser_timeout_seconds: float = 15.0
    parser_max_retries: int = 3
    use_selenium_fallback: bool = True

    max_tracks_per_user: int = 50
    cache_ttl_seconds: int = 3600

    database_path: str = "./data/bot.db"
    log_level: str = "INFO"
    log_dir: str = "./data/logs"

    @property
    def db_path(self) -> Path:
        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_path(self) -> Path:
        path = Path(self.log_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
