from datetime import date, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin


class FAERSQuarterlyMetadataModel(Base, TimestampMixin):
    __tablename__ = "faers_quarterly_metadata"

    release_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    quarter: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    dataset_release: Mapped[str] = mapped_column(String(100), nullable=False)
    import_date: Mapped[date] = mapped_column(Date, nullable=False)
    processing_version: Mapped[str] = mapped_column(String(50), nullable=False)
    total_reports: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ProcessedReportModel(Base, TimestampMixin):
    __tablename__ = "processed_reports"

    report_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reactions: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    patient_age: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    patient_sex: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    event_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    seriousness: Mapped[str] = mapped_column(String(20), nullable=False, default="Unknown")
    seriousness_codes: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    report_quarter: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="FDA_FAERS")


class DrugEventPairModel(Base):
    __tablename__ = "drug_event_pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quarter: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)


class SignalModel(Base, TimestampMixin):
    __tablename__ = "signals"

    signal_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    supporting_report_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prr: Mapped[float] = mapped_column(Float, nullable=False)
    ror: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trend_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    priority_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    candidate_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="candidate"
    )
    dataset_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    known_limitations: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True, default=list
    )


class SignalReviewModel(Base, TimestampMixin):
    __tablename__ = "signal_reviews"

    review_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    signal_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("signals.signal_id"), nullable=False, unique=True, index=True
    )
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_started"
    )
    evidence_checklist: Mapped[Dict[str, bool]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    reviewer_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewer_conclusion: Mapped[str] = mapped_column(Text, nullable=False, default="")


class SignalMetricsModel(Base, TimestampMixin):
    __tablename__ = "signal_metrics"

    signal_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    prr: Mapped[float] = mapped_column(Float, nullable=False)
    ror: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    report_count: Mapped[int] = mapped_column(Integer, nullable=False)
    contingency_table: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    trend_data: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    chi_square: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class CaseQualityModel(Base, TimestampMixin):
    __tablename__ = "case_quality"

    signal_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    total_reports: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_age_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_sex_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_date_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    quality_flags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    indicators: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)


class DuplicateCandidateModel(Base, TimestampMixin):
    __tablename__ = "duplicate_candidates"

    candidate_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    signal_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    report_id_a: Mapped[str] = mapped_column(String(50), nullable=False)
    report_id_b: Mapped[str] = mapped_column(String(50), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    drug_similarity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    event_similarity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    date_proximity_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    matched_fields: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="potential_duplicate"
    )


class AISummaryModel(Base, TimestampMixin):
    __tablename__ = "ai_summaries"

    summary_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    signal_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    why_flagged: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    suggested_questions: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class DocumentUploadModel(Base, TimestampMixin):
    __tablename__ = "document_uploads"

    document_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_text_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class DocumentAnalysisModel(Base, TimestampMixin):
    __tablename__ = "document_analysis"

    analysis_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    signal_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    relevant_sections: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    existing_related_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    potential_coverage_gap: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    human_review_required: Mapped[bool] = mapped_column(nullable=False, default=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    disclaimer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


