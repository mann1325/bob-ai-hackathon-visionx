from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(database_url: Optional[str]) -> Optional[str]:
    if not database_url:
        return None
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg2://" + database_url[len("postgres://") :]
    return database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_port: int = 8000
    app_name: str = "SignalTrace API"

    database_url: Optional[str] = None

    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    openfda_api_base_url: str = "https://api.fda.gov"
    openfda_api_key: Optional[str] = None

    # Document upload settings (Phase 6)
    upload_dir: str = "data/uploads"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB limit

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @property
    def sqlalchemy_database_url(self) -> Optional[str]:
        """Return a SQLAlchemy-compatible URL for local and Render databases."""
        return normalize_database_url(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
