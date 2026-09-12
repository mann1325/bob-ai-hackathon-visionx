from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import (
    CaseQualityModel,
    DuplicateCandidateModel,
    ProcessedReportModel,
    SignalModel,
)
from shared.schemas.evidence import (
    CaseQualityIndicator,
    CaseQualityReport,
    DuplicateCandidate,
)


def get_case_quality_for_signal(
    db: Session, signal_id: str
) -> Optional[CaseQualityReport]:
    """Retrieve or compute case quality metrics for a candidate signal."""
    sig_stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
    sig = db.scalars(sig_stmt).first()
    if not sig:
        return None

    # Check pre-materialized case quality table
    cq_stmt = select(CaseQualityModel).where(CaseQualityModel.signal_id == signal_id)
    cq = db.scalars(cq_stmt).first()
    if cq:
        return CaseQualityReport(
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

    # Compute on read from processed reports if table is not pre-populated
    report_stmt = select(ProcessedReportModel).where(
        func.upper(ProcessedReportModel.drug_name) == sig.drug_name.upper()
    )
    reports = db.scalars(report_stmt).all()
    total = len(reports) if reports else sig.supporting_report_count

    if total == 0:
        return CaseQualityReport(
            signal_id=sig.signal_id,
            total_reports=0,
            missing_age_count=0,
            missing_sex_count=0,
            missing_date_count=0,
            quality_score=1.0,
            quality_flags=[],
            indicators=[],
        )

    missing_age = sum(1 for r in reports if r.patient_age is None) if reports else 0
    missing_sex = (
        sum(1 for r in reports if not r.patient_sex or r.patient_sex.strip() == "")
        if reports
        else 0
    )
    missing_date = (
        sum(1 for r in reports if not r.event_date or r.event_date.strip() == "")
        if reports
        else 0
    )

    quality_flags: List[str] = []
    indicators: List[CaseQualityIndicator] = []

    age_pct = (missing_age / total) if total > 0 else 0
    if age_pct > 0.3:
        quality_flags.append("high_missing_age")
        indicators.append(
            CaseQualityIndicator(
                flag="high_missing_age",
                description=f"{int(age_pct * 100)}% of reports are missing patient age.",
                impact_level="high",
            )
        )
    elif age_pct > 0:
        quality_flags.append("minor_missing_age")
        indicators.append(
            CaseQualityIndicator(
                flag="minor_missing_age",
                description=f"{int(age_pct * 100)}% of reports are missing patient age.",
                impact_level="low",
            )
        )

    sex_pct = (missing_sex / total) if total > 0 else 0
    if sex_pct > 0.3:
        quality_flags.append("high_missing_sex")
        indicators.append(
            CaseQualityIndicator(
                flag="high_missing_sex",
                description=f"{int(sex_pct * 100)}% of reports are missing patient sex.",
                impact_level="medium",
            )
        )

    date_pct = (missing_date / total) if total > 0 else 0
    if date_pct > 0.3:
        quality_flags.append("high_missing_date")
        indicators.append(
            CaseQualityIndicator(
                flag="high_missing_date",
                description=f"{int(date_pct * 100)}% of reports are missing event onset date.",
                impact_level="high",
            )
        )

    # Composite score formula: penalize missing fields
    penalty = (age_pct * 0.3) + (sex_pct * 0.3) + (date_pct * 0.4)
    quality_score = max(0.0, round(1.0 - penalty, 2))

    return CaseQualityReport(
        signal_id=sig.signal_id,
        total_reports=total,
        missing_age_count=missing_age,
        missing_sex_count=missing_sex,
        missing_date_count=missing_date,
        quality_score=quality_score,
        quality_flags=quality_flags,
        indicators=indicators,
    )


def get_duplicate_candidates_for_signal(
    db: Session, signal_id: str
) -> Optional[List[DuplicateCandidate]]:
    """Retrieve potential duplicate report candidates for a signal."""
    sig_stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
    sig = db.scalars(sig_stmt).first()
    if not sig:
        return None

    # Check pre-materialized duplicate candidates table
    dup_stmt = select(DuplicateCandidateModel).where(
        DuplicateCandidateModel.signal_id == signal_id
    )
    dups = db.scalars(dup_stmt).all()
    if dups:
        return [
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

    # If not pre-materialized, return empty candidate list (never invent fake matches)
    return []
