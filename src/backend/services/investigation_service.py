import hashlib
from itertools import combinations
from typing import Dict, List, Optional, Tuple
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
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


def _duplicate_candidate_from_model(candidate: DuplicateCandidateModel) -> DuplicateCandidate:
    return DuplicateCandidate(
        candidate_id=candidate.candidate_id,
        report_id_a=candidate.report_id_a,
        report_id_b=candidate.report_id_b,
        rationale=candidate.rationale,
        status=candidate.status,
        similarity_score=candidate.similarity_score,
        drug_similarity=candidate.drug_similarity,
        event_similarity=candidate.event_similarity,
        date_proximity_days=candidate.date_proximity_days,
        matched_fields=candidate.matched_fields or [],
    )


def _report_block_key(report: ProcessedReportModel) -> Optional[Tuple[float, str, str]]:
    """Return a strict duplicate block key from complete identifying fields."""
    if report.patient_age is None or not report.patient_sex or not report.event_date:
        return None
    return (
        float(report.patient_age),
        report.patient_sex.strip().upper(),
        report.event_date.strip(),
    )


def _build_potential_duplicate(
    signal: SignalModel,
    report_a: ProcessedReportModel,
    report_b: ProcessedReportModel,
    block_key: Tuple[float, str, str],
) -> DuplicateCandidateModel:
    report_ids = sorted((report_a.report_id, report_b.report_id))
    candidate_key = "|".join((signal.signal_id, *report_ids))
    candidate_id = f"DUP-{hashlib.sha256(candidate_key.encode('utf-8')).hexdigest()[:12].upper()}"
    age, sex, event_date = block_key
    rationale = (
        f"Potential duplicate review: reports {report_ids[0]} and {report_ids[1]} "
        f"share drug '{signal.drug_name}', event '{signal.event_name}', "
        f"patient age {age:g}, sex '{sex}', and event date {event_date}. "
        "Exact field overlap is a triage signal only and is not confirmation of duplication."
    )
    return DuplicateCandidateModel(
        candidate_id=candidate_id,
        signal_id=signal.signal_id,
        report_id_a=report_ids[0],
        report_id_b=report_ids[1],
        rationale=rationale,
        similarity_score=1.0,
        drug_similarity=1.0,
        event_similarity=1.0,
        date_proximity_days=0,
        matched_fields=["drug", "event", "age", "sex", "event_date"],
        status="potential_duplicate",
    )


def _generate_duplicate_candidates(
    db: Session,
    signal: SignalModel,
) -> List[DuplicateCandidateModel]:
    """Generate candidates using strict indexed drug/quarter and field blocks."""
    report_query = (
        select(ProcessedReportModel)
        .where(func.upper(ProcessedReportModel.drug_name) == signal.drug_name.upper())
        .order_by(ProcessedReportModel.report_id)
    )
    if signal.dataset_version:
        report_query = report_query.where(
            ProcessedReportModel.report_quarter == signal.dataset_version
        )

    blocks: Dict[Tuple[float, str, str], List[ProcessedReportModel]] = {}
    for report in db.scalars(report_query).all():
        reactions = report.reactions if isinstance(report.reactions, list) else []
        if signal.event_name not in reactions:
            continue
        block_key = _report_block_key(report)
        if block_key is not None:
            blocks.setdefault(block_key, []).append(report)

    candidates: List[DuplicateCandidateModel] = []
    for block_key in sorted(blocks, key=lambda key: tuple(str(value) for value in key)):
        reports = blocks[block_key]
        for report_a, report_b in combinations(reports, 2):
            if report_a.report_id == report_b.report_id:
                continue
            candidates.append(
                _build_potential_duplicate(signal, report_a, report_b, block_key)
            )
    return candidates


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

    # Compute on read from the same drug/event/quarter scope as supporting reports.
    report_filters = [ProcessedReportModel.drug_name == sig.drug_name]
    if sig.dataset_version:
        report_filters.append(ProcessedReportModel.report_quarter == sig.dataset_version)

    if db.get_bind().dialect.name == "postgresql":
        report_filters.append(
            cast(ProcessedReportModel.reactions, JSONB).contains([sig.event_name.upper()])
        )
        reports = db.scalars(
            select(ProcessedReportModel).where(*report_filters)
        ).all()
    else:
        # SQLite is used by the existing test suite and has no JSONB containment operator.
        candidates = db.scalars(select(ProcessedReportModel).where(*report_filters)).all()
        event_name = sig.event_name.upper()
        reports = [
            report
            for report in candidates
            if isinstance(report.reactions, list)
            and any(
                isinstance(reaction, str) and reaction.upper() == event_name
                for reaction in report.reactions
            )
        ]
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
    """Retrieve or materialize potential duplicate candidates for a signal."""
    sig_stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
    sig = db.scalars(sig_stmt).first()
    if not sig:
        return None

    # Check pre-materialized duplicate candidates table
    dup_stmt = select(DuplicateCandidateModel).where(
        DuplicateCandidateModel.signal_id == signal_id
    )
    dups = db.scalars(dup_stmt.order_by(DuplicateCandidateModel.candidate_id)).all()
    if dups:
        return [_duplicate_candidate_from_model(candidate) for candidate in dups]

    generated = _generate_duplicate_candidates(db, sig)
    if not generated:
        return []

    db.add_all(generated)
    db.commit()
    return [_duplicate_candidate_from_model(candidate) for candidate in generated]
