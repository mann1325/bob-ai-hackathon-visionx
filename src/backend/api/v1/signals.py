import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from rules.engine import evaluate_regulatory_impact
from services.explanation_service import generate_signal_explanation
from services.investigation_service import (
    get_case_quality_for_signal,
    get_duplicate_candidates_for_signal,
)
from services.signal_service import (
    get_signal_detail,
    get_signal_evidence,
    get_signal_metrics,
    list_signals,
)
from shared.schemas.ai import GroqExplanation
from shared.schemas.common import PaginatedResponse
from shared.schemas.evidence import (
    CaseQualityReport,
    DuplicateCandidate,
    EvidenceBundle,
)
from shared.schemas.regulatory import RegulatoryImpact
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


@router.get("/{signal_id}/case-quality", response_model=CaseQualityReport)
def get_signal_case_quality(
    signal_id: str,
    db: Session = Depends(get_db),
) -> CaseQualityReport:
    """Retrieve case quality indicators and flags for a candidate signal."""
    quality = get_case_quality_for_signal(db, signal_id)
    if not quality:
        raise HTTPException(
            status_code=404,
            detail=f"Signal '{signal_id}' not found for case quality evaluation.",
        )
    return quality


@router.get("/{signal_id}/duplicates", response_model=List[DuplicateCandidate])
def get_signal_duplicates(
    signal_id: str,
    db: Session = Depends(get_db),
) -> List[DuplicateCandidate]:
    """Retrieve potential duplicate candidates for a signal with similarity rationale."""
    duplicates = get_duplicate_candidates_for_signal(db, signal_id)
    if duplicates is None:
        raise HTTPException(
            status_code=404,
            detail=f"Signal '{signal_id}' not found for duplicate evaluation.",
        )
    return duplicates


@router.post("/{signal_id}/explain", response_model=GroqExplanation)
@router.post("/{signal_id}/explanation", response_model=GroqExplanation, include_in_schema=False)
def explain_signal(
    signal_id: str,
    db: Session = Depends(get_db),
) -> GroqExplanation:
    """Generate structured evidence explanation using Groq with backend facts only."""
    explanation = generate_signal_explanation(db, signal_id)
    if not explanation:
        raise HTTPException(
            status_code=404,
            detail=f"Signal '{signal_id}' not found for explanation.",
        )
    return explanation


@router.get("/{signal_id}/regulatory-impact", response_model=RegulatoryImpact)
def get_signal_regulatory_impact(
    signal_id: str,
    db: Session = Depends(get_db),
) -> RegulatoryImpact:
    """Evaluate deterministic regulatory impact and return potential review areas."""
    impact = evaluate_regulatory_impact(db, signal_id)
    if not impact:
        raise HTTPException(
            status_code=404,
            detail=f"Signal '{signal_id}' not found for regulatory impact evaluation.",
        )
    return impact


@router.get("/{signal_id}/documents")
def get_signal_documents_endpoint(
    signal_id: str,
    db: Session = Depends(get_db),
):
    """List all uploaded documents and their analyses associated with a signal."""
    from services.document_analysis_service import get_documents_for_signal
    from services.signal_service import get_signal_detail

    signal = get_signal_detail(db, signal_id)
    if not signal:
        raise HTTPException(
            status_code=404,
            detail=f"Signal '{signal_id}' not found.",
        )

    return get_documents_for_signal(db, signal_id)

