import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from services.signal_service import (
    get_signal_detail,
    get_signal_evidence,
    get_signal_metrics,
    list_signals,
)
from shared.schemas.common import PaginatedResponse
from shared.schemas.evidence import EvidenceBundle
from shared.schemas.signal import SignalDetail, SignalMetrics, SignalSummary

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=PaginatedResponse[SignalSummary])
def get_candidate_signals(
    drug: Optional[str] = Query(None, description="Filter by drug name"),
    event: Optional[str] = Query(None, description="Filter by adverse event name"),
    min_prr: Optional[float] = Query(None, ge=0.0, description="Minimum PRR threshold"),
    status: Optional[str] = Query(None, description="Candidate status (candidate/under_review/closed)"),
    release_id: Optional[str] = Query(None, description="Filter by FAERS dataset release (e.g. 2024Q1)"),
    sort_by: str = Query("rank", description="Sort column (rank, prr, supporting_report_count, drug_name)"),
    sort_order: str = Query("asc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[SignalSummary]:
    """List candidate drug-event signals with filtering, sorting, and pagination."""
    items, total = list_signals(
        db=db,
        drug=drug,
        event=event,
        min_prr=min_prr,
        status=status,
        release_id=release_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse[SignalSummary](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{signal_id}", response_model=SignalDetail)
def get_signal_by_id(
    signal_id: str,
    db: Session = Depends(get_db),
) -> SignalDetail:
    """Retrieve full detail for a specific candidate safety signal."""
    signal = get_signal_detail(db, signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate signal '{signal_id}' not found.",
        )
    return signal


@router.get("/{signal_id}/metrics", response_model=SignalMetrics)
def get_signal_metrics_by_id(
    signal_id: str,
    db: Session = Depends(get_db),
) -> SignalMetrics:
    """Retrieve supporting statistical metrics (PRR, ROR, counts, contingency table, trend)."""
    metrics = get_signal_metrics(db, signal_id)
    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"Metrics for signal '{signal_id}' not found.",
        )
    return metrics


@router.get("/{signal_id}/evidence", response_model=EvidenceBundle)
def get_signal_evidence_by_id(
    signal_id: str,
    db: Session = Depends(get_db),
) -> EvidenceBundle:
    """Retrieve structured evidence bundle for dashboard inspection or AI explanation."""
    evidence = get_signal_evidence(db, signal_id)
    if not evidence:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence for signal '{signal_id}' not found.",
        )
    return evidence
