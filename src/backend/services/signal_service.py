import math
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from database.models import (
    CaseQualityModel,
    DrugEventPairModel,
    DuplicateCandidateModel,
    FAERSQuarterlyMetadataModel,
    ProcessedReportModel,
    SignalMetricsModel,
    SignalModel,
)
from shared.schemas.evidence import (
    CaseQualityIndicator,
    CaseQualityReport,
    DuplicateCandidate,
    EvidenceBundle,
)
from shared.schemas.signal import (
    SignalDetail,
    SignalMetrics,
    SignalSummary,
)


def search_drugs(db: Session, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search for drug names matching the query string."""
    q_str = f"%{query.strip().upper()}%"

    # Search in signals table first
    stmt_signals = (
        select(SignalModel.drug_name, func.count(SignalModel.signal_id).label("signal_count"))
        .where(func.upper(SignalModel.drug_name).like(q_str))
        .group_by(SignalModel.drug_name)
        .order_by(func.count(SignalModel.signal_id).desc())
        .limit(limit)
    )
    results = db.execute(stmt_signals).all()

    if results:
        return [
            {"drug_name": r[0], "candidate_signals_count": r[1]}
            for r in results
        ]

    # Fallback to processed reports or drug event pairs
    stmt_reports = (
        select(distinct(ProcessedReportModel.drug_name))
        .where(func.upper(ProcessedReportModel.drug_name).like(q_str))
        .limit(limit)
    )
    report_drugs = db.scalars(stmt_reports).all()

    return [
        {"drug_name": d, "candidate_signals_count": 0}
        for d in report_drugs
    ]


def list_signals(
    db: Session,
    drug: Optional[str] = None,
    event: Optional[str] = None,
    min_prr: Optional[float] = None,
    status: Optional[str] = None,
    release_id: Optional[str] = None,
    sort_by: str = "rank",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[SignalSummary], int]:
    """List candidate signals with filtering, sorting, and pagination."""
    query = select(SignalModel)

    if drug:
        query = query.where(func.upper(SignalModel.drug_name).like(f"%{drug.strip().upper()}%"))
    if event:
        query = query.where(func.upper(SignalModel.event_name).like(f"%{event.strip().upper()}%"))
    if min_prr is not None:
        query = query.where(SignalModel.prr >= min_prr)
    if status:
        query = query.where(SignalModel.candidate_status == status)
    if release_id:
        query = query.where(SignalModel.dataset_version == release_id)

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_stmt) or 0

    # Sorting
    sort_col = getattr(SignalModel, sort_by, SignalModel.rank)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_col.desc().nulls_last())
    else:
        query = query.order_by(sort_col.asc().nulls_last())

    # Pagination
    offset = max(0, (page - 1) * page_size)
    query = query.offset(offset).limit(page_size)

    records = db.scalars(query).all()

    items = [
        SignalSummary(
            signal_id=r.signal_id,
            drug_name=r.drug_name,
            event_name=r.event_name,
            supporting_report_count=r.supporting_report_count,
            prr=r.prr,
            ror=r.ror,
            trend_score=r.trend_score,
            risk_score=r.risk_score,
            priority_level=r.priority_level,
            candidate_status=r.candidate_status,
            dataset_version=r.dataset_version,
            rank=r.rank,
        )
        for r in records
    ]

    return items, total


def get_signal_detail(db: Session, signal_id: str) -> Optional[SignalDetail]:
    """Retrieve full details for a candidate signal."""
    stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
    r = db.scalars(stmt).first()
    if not r:
        return None

    metrics = get_signal_metrics(db, signal_id)
    dataset_metadata = None
    dataset_source = None
    if r.dataset_version:
        dataset_metadata = db.scalars(
            select(FAERSQuarterlyMetadataModel).where(
                FAERSQuarterlyMetadataModel.release_id == r.dataset_version
            )
        ).first()
        source = db.scalars(
            select(ProcessedReportModel.source)
            .where(ProcessedReportModel.report_quarter == r.dataset_version)
            .limit(1)
        ).first()
        if source:
            dataset_source = source.replace("_", " ")

    return SignalDetail(
        signal_id=r.signal_id,
        drug_name=r.drug_name,
        event_name=r.event_name,
        supporting_report_count=r.supporting_report_count,
        prr=r.prr,
        ror=r.ror,
        trend_score=r.trend_score,
        risk_score=r.risk_score,
        priority_level=r.priority_level,
        candidate_status=r.candidate_status,
        dataset_version=r.dataset_version,
        dataset_source=dataset_source,
        processing_version=(dataset_metadata.processing_version if dataset_metadata else None),
        import_date=(dataset_metadata.import_date if dataset_metadata else None),
        metrics=metrics,
        known_limitations=r.known_limitations or [
            "FAERS reports represent spontaneous reports and do not prove causality.",
            "Underreporting and reporting bias are inherent limitations of spontaneous data.",
        ],
        human_review_required=True,
    )


def get_signal_metrics(db: Session, signal_id: str) -> Optional[SignalMetrics]:
    """Retrieve supporting metrics for a candidate signal."""
    stmt = select(SignalMetricsModel).where(SignalMetricsModel.signal_id == signal_id)
    m = db.scalars(stmt).first()
    if m:
        return SignalMetrics(
            signal_id=m.signal_id,
            prr=m.prr,
            ror=m.ror,
            report_count=m.report_count,
            contingency_table=m.contingency_table,
            trend_data=m.trend_data,
            chi_square=m.chi_square,
        )

    # Fallback to base signal if metrics row not separately materialized
    sig_stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
    sig = db.scalars(sig_stmt).first()
    if not sig:
        return None

    return SignalMetrics(
        signal_id=sig.signal_id,
        prr=sig.prr,
        ror=sig.ror,
        report_count=sig.supporting_report_count,
    )


def get_signal_evidence(db: Session, signal_id: str) -> Optional[EvidenceBundle]:
    """Construct a structured evidence bundle for a signal."""
    sig_stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
    sig = db.scalars(sig_stmt).first()
    if not sig:
        return None

    # Retrieve metrics
    metrics = get_signal_metrics(db, signal_id)
    metrics_dict = (
        metrics.model_dump()
        if metrics
        else {
            "prr": sig.prr,
            "ror": sig.ror,
            "report_count": sig.supporting_report_count,
            "trend_score": sig.trend_score,
        }
    )

    # Retrieve case quality
    cq_stmt = select(CaseQualityModel).where(CaseQualityModel.signal_id == signal_id)
    cq = db.scalars(cq_stmt).first()
    case_quality_report = None
    if cq:
        case_quality_report = CaseQualityReport(
            signal_id=cq.signal_id,
            total_reports=cq.total_reports,
            missing_age_count=cq.missing_age_count,
            missing_sex_count=cq.missing_sex_count,
            missing_date_count=cq.missing_date_count,
            quality_score=cq.quality_score,
            quality_flags=cq.quality_flags or [],
            indicators=[
                CaseQualityIndicator(**ind) if isinstance(ind, dict) else ind
                for ind in (cq.indicators or [])
            ],
        )

    # Retrieve potential duplicate candidates
    dup_stmt = select(DuplicateCandidateModel).where(
        DuplicateCandidateModel.signal_id == signal_id
    )
    dups = db.scalars(dup_stmt).all()
    duplicate_candidates = [
        DuplicateCandidate(
            candidate_id=d.candidate_id,
            report_id_a=d.report_id_a,
            report_id_b=d.report_id_b,
            rationale=d.rationale,
            status=d.status,
            similarity_score=d.similarity_score,
            drug_similarity=d.drug_similarity,
            event_similarity=d.event_similarity,
            date_proximity_days=d.date_proximity_days,
            matched_fields=d.matched_fields or [],
        )
        for d in dups
    ]

    return EvidenceBundle(
        signal_id=sig.signal_id,
        drug_name=sig.drug_name,
        event_name=sig.event_name,
        metrics=metrics_dict,
        case_quality=case_quality_report,
        potential_duplicates=duplicate_candidates,
        known_limitations=sig.known_limitations or [
            "FAERS spontaneous reporting bias.",
            "Cannot establish direct drug-event causality.",
        ],
        human_review_required=True,
    )
