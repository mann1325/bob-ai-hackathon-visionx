from fastapi import APIRouter

from api.v1.datasets import router as datasets_router
from api.v1.documents import router as documents_router
from api.v1.drugs import router as drugs_router
from api.v1.health import router as health_router
from api.v1.investigation import router as investigation_router
from api.v1.ingest import router as ingest_router
from api.v1.openfda import router as openfda_router
from api.v1.regulatory import router as regulatory_router
from api.v1.reports import router as reports_router
from api.v1.reviews import router as reviews_router
from api.v1.signals import router as signals_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(investigation_router)
api_v1_router.include_router(datasets_router)
api_v1_router.include_router(drugs_router)
api_v1_router.include_router(signals_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(reviews_router)
api_v1_router.include_router(regulatory_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(ingest_router)
api_v1_router.include_router(openfda_router)
