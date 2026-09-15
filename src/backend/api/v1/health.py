from fastapi import APIRouter, Depends, Response

from app.config import Settings
from app.dependencies import get_app_settings

router = APIRouter(tags=["health"])


@router.head("/health", status_code=200)
def health_head() -> Response:
    return Response(status_code=200)


@router.get("/health")
def health_check(settings: Settings = Depends(get_app_settings)) -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }
