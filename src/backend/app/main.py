import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_exception_handlers
from api.v1.router import api_v1_router
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "SignalTrace backend — serves deterministic signal data, "
            "investigation APIs, and AI-assisted explanation layers."
        ),
        debug=settings.is_development,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router)

    @app.get("/", tags=["root"])
    def root() -> dict:
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    logger.info("SignalTrace API initialized (env=%s)", settings.app_env)
    return app


app = create_app()
