from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    DEFAULT_PAGE_SIZE: int = 10
    """Page size for fetching data from the database"""

    RUN_MIGRATIONS_UPON_LAUNCH: bool = False
    """Off by default: on Vercel it would run on every cold start"""

    GLOBAL_API_PREFIX: str = "/api"

    DATABASE_URL: str = (
        "postgresql://user:password@localhost:5432/couple_bot"
    )

    API_TOKEN: str = ""
    """Bearer token for the /api routes. Empty refuses every request"""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding="utf-8",
    )


CONFIG = Config()

fastapi_config: dict[str, Any] = {
    "title": "Couple Bot API",
    "version": CONFIG.APP_VERSION,
    "redirect_slashes": False,
    "debug": CONFIG.DEBUG,
    "swagger_ui_parameters": {"filter": True},
}

if not CONFIG.DEBUG:
    fastapi_config.update(
        {"docs_url": None, "redoc_url": None, "openapi_url": None}
    )
