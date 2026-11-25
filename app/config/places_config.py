from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class PlacesConfig(BaseSettings):
    PLACE_MIN_SCORE: int = 1
    PLACE_MAX_SCORE: int = 10
    """Place review score bounds; the DB check constraint is set by the
    migration, so changing these needs a new migration too"""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding="utf-8",
    )


config = PlacesConfig()
