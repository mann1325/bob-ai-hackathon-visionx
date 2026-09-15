"""
POST /api/v1/ingest  — trigger FDA FAERS quarterly ZIP ingestion.

Accepts a local ZIP file path and a quarter identifier.
Returns job status and row counts on success.
Returns 409 Conflict if the quarter has already been imported.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies import get_db
from services.faers_ingestion_service import (
    FAERSAlreadyImportedError,
    ingest_faers_zip,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


# ---------------------------------------------------------------------------
# Request / response schemas  (ingest-only, not in shared schemas)
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    quarter: str = Field(
        ...,
        description="Quarter identifier, e.g. '2024Q1'",
        examples=["2024Q1"],
    )
    zip_path: str = Field(
        ...,
        description="Absolute or relative path to the official FDA FAERS ASCII ZIP file",
        examples=["/data/faers_ascii_2024q1.zip"],
    )
    processing_version: Optional[str] = Field(
        default="v1.0.0",
        description="Version tag recorded in dataset metadata",
    )


class IngestResponse(BaseModel):
    release_id: str
    quarter: str
    reports_inserted: int
    pairs_upserted: int
    status: str = "completed"
    message: str


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("", response_model=IngestResponse, status_code=201)
def trigger_ingestion(
    body: IngestRequest,
    db: Session = Depends(get_db),
) -> IngestResponse:
    """
    Ingest an official FDA FAERS quarterly ASCII ZIP file.

    The ZIP must be accessible at the given `zip_path` on the server's filesystem.
    The quarter must not have been previously imported (idempotency guard).

    This endpoint is intended for data pipeline / admin use only.
    It does not compute PRR/ROR or populate the signals table — that is handled
    by the ML pipeline (Member 2 scope).
    """
    release_id = body.quarter.strip().upper()
    logger.info(
        "Ingestion requested: quarter=%s zip_path=%s", release_id, body.zip_path
    )

    try:
        reports_inserted, pairs_upserted = ingest_faers_zip(
            db=db,
            quarter=release_id,
            zip_path=body.zip_path,
            processing_version=body.processing_version or "v1.0.0",
        )
    except FAERSAlreadyImportedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"ZIP file not found: {exc}",
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Required file missing inside ZIP: {exc}",
        )
    except Exception as exc:
        logger.exception("Ingestion failed for quarter=%s", release_id)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {exc}",
        )

    db.commit()
    logger.info(
        "Ingestion committed: quarter=%s reports=%d pairs=%d",
        release_id,
        reports_inserted,
        pairs_upserted,
    )

    return IngestResponse(
        release_id=release_id,
        quarter=release_id,
        reports_inserted=reports_inserted,
        pairs_upserted=pairs_upserted,
        status="completed",
        message=(
            f"Successfully ingested {reports_inserted} reports and "
            f"{pairs_upserted} drug-event pairs for quarter {release_id}. "
            "PRR/ROR computation is handled by the ML pipeline."
        ),
    )
