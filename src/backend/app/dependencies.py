from app.config import Settings, get_settings
from database.session import get_db


def get_app_settings() -> Settings:
    return get_settings()


__all__ = ["Settings", "get_settings", "get_app_settings", "get_db"]
