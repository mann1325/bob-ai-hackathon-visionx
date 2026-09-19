from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from services.investigation_summary_service import get_investigation_summary
from shared.schemas.investigation import InvestigationSummary

router = APIRouter(prefix="/signals", tags=["investigation"])


@router.get("/{signal_id}/investigation-summary", response_model=InvestigationSummary)
def get_investigation_summary_endpoint(
    signal_id: str,
    db: Session = Depends(get_db),
) -> InvestigationSummary:
    summary = get_investigation_summary(db, signal_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"Candidate signal '{signal_id}' not found.")
    return summary