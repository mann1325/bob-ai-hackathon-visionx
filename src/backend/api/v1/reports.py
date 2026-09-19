from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from services.signal_service import get_processed_report
from shared.schemas.signal import NormalizedReport

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_id}", response_model=NormalizedReport)
def get_report_by_id(
    report_id: str,
    db: Session = Depends(get_db),
) -> NormalizedReport:
    """Retrieve one stored processed FAERS report."""
    report = get_processed_report(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Processed report '{report_id}' not found.",
        )
    return report