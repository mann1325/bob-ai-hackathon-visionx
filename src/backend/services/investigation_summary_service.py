from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import (
    AISummaryModel,
    DocumentAnalysisModel,
    DocumentUploadModel,
    DuplicateCandidateModel,
    SignalModel,
)
from rules.engine import evaluate_regulatory_impact
from services.investigation_service import get_case_quality_for_signal
from services.review_service import get_signal_review
from services.signal_service import get_signal_evidence, get_signal_metrics
from shared.schemas.investigation import InvestigationDocumentSummary, InvestigationSummary


def _why_flagged(signal: SignalModel) -> str:
    return (
        f"{signal.drug_name} and {signal.event_name} form a candidate signal "
        f"supported by {signal.supporting_report_count} reports with a PRR of "
        f"{signal.prr:.2f}."
    )


def get_investigation_summary(
    db: Session, signal_id: str
) -> Optional[InvestigationSummary]:
    signal = db.scalars(
        select(SignalModel).where(SignalModel.signal_id == signal_id)
    ).first()
    if signal is None:
        return None

    metrics = get_signal_metrics(db, signal_id)
    quality = get_case_quality_for_signal(db, signal_id)
    regulatory = evaluate_regulatory_impact(db, signal_id)
    review = get_signal_review(db, signal_id)

    duplicate_count = db.scalar(
        select(func.count()).select_from(DuplicateCandidateModel).where(
            DuplicateCandidateModel.signal_id == signal_id
        )
    ) or 0
    duplicate_rows = db.scalars(
        select(DuplicateCandidateModel)
        .where(DuplicateCandidateModel.signal_id == signal_id)
        .order_by(DuplicateCandidateModel.candidate_id)
        .limit(3)
    ).all()

    ai_summary = db.scalars(
        select(AISummaryModel)
        .where(AISummaryModel.signal_id == signal_id)
        .order_by(AISummaryModel.created_at.desc())
    ).first()

    documents = db.scalars(
        select(DocumentUploadModel)
        .where(DocumentUploadModel.signal_id == signal_id)
        .order_by(DocumentUploadModel.created_at.desc())
    ).all()
    document_ids = [document.document_id for document in documents]
    analyses = {}
    if document_ids:
        analysis_rows = db.scalars(
            select(DocumentAnalysisModel)
            .where(DocumentAnalysisModel.document_id.in_(document_ids))
            .order_by(DocumentAnalysisModel.created_at.desc())
        ).all()
        for analysis in analysis_rows:
            analyses.setdefault(analysis.document_id, analysis)

    document_summaries = [
        InvestigationDocumentSummary(
            document_id=document.document_id,
            filename=document.filename,
            analysis_status=(analyses[document.document_id].analysis_status if document.document_id in analyses else None),
            relevant_section_count=(len(analyses[document.document_id].relevant_sections or []) if document.document_id in analyses else 0),
            potential_coverage_gap=(analyses[document.document_id].potential_coverage_gap if document.document_id in analyses else None),
            human_review_required=(analyses[document.document_id].human_review_required if document.document_id in analyses else True),
        )
        for document in documents
    ]

    review_data: Optional[Dict[str, Any]] = review.model_dump(mode="json") if review else None
    ai_data: Optional[Dict[str, Any]] = None
    if ai_summary:
        ai_data = {
            "why_flagged": ai_summary.why_flagged,
            "evidence_summary": ai_summary.evidence_summary,
            "limitations": ai_summary.limitations or [],
            "suggested_questions": ai_summary.suggested_questions or [],
            "model_used": ai_summary.model_used,
            "created_at": ai_summary.created_at,
            "advisory": True,
        }

    return InvestigationSummary(
        signal_id=signal.signal_id,
        drug_name=signal.drug_name,
        event_name=signal.event_name,
        dataset_version=signal.dataset_version,
        candidate_status=signal.candidate_status,
        priority_level=signal.priority_level,
        supporting_report_count=signal.supporting_report_count,
        prr=signal.prr,
        ror=signal.ror,
        chi_square=metrics.chi_square if metrics else None,
        trend_score=signal.trend_score,
        trend_data=metrics.trend_data if metrics else None,
        why_flagged=_why_flagged(signal),
        known_limitations=signal.known_limitations or [],
        case_quality=(quality.model_dump() if quality else None),
        duplicate_count=duplicate_count,
        duplicates=[
            {
                "candidate_id": duplicate.candidate_id,
                "report_id_a": duplicate.report_id_a,
                "report_id_b": duplicate.report_id_b,
                "status": duplicate.status,
                "similarity_score": duplicate.similarity_score,
                "matched_fields": duplicate.matched_fields or [],
                "human_review_required": True,
            }
            for duplicate in duplicate_rows
        ],
        ai_explanation=ai_data,
        regulatory_review_areas=(
            [area.model_dump() for area in regulatory.review_areas]
            if regulatory
            else []
        ),
        regulatory_rule_matches=(
            [match.model_dump() for match in regulatory.rule_matches]
            if regulatory
            else []
        ),
        documents=document_summaries,
        human_review=review_data,
        human_review_required=True,
    )
