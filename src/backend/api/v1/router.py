from fastapi import APIRouter

from api.v1.datasets import router as datasets_router
from api.v1.drugs import router as drugs_router
from api.v1.health import router as health_router
from api.v1.regulatory import router as regulatory_router
from api.v1.signals import router as signals_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(datasets_router)
api_v1_router.include_router(drugs_router)
api_v1_router.include_router(signals_router)
api_v1_router.include_router(regulatory_router)
