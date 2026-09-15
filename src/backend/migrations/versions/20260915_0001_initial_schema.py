"""Create the initial SignalTrace schema.

Revision ID: 20260915_0001
Revises:
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260915_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "faers_quarterly_metadata",
        sa.Column("release_id", sa.String(length=50), nullable=False),
        sa.Column("quarter", sa.String(length=20), nullable=False),
        sa.Column("dataset_release", sa.String(length=100), nullable=False),
        sa.Column("import_date", sa.Date(), nullable=False),
        sa.Column("processing_version", sa.String(length=50), nullable=False),
        sa.Column("total_reports", sa.Integer(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("release_id"),
    )
    op.create_index(
        "ix_faers_quarterly_metadata_quarter",
        "faers_quarterly_metadata",
        ["quarter"],
    )

    op.create_table(
        "processed_reports",
        sa.Column("report_id", sa.String(length=50), nullable=False),
        sa.Column("drug_name", sa.String(length=255), nullable=False),
        sa.Column("reactions", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("patient_age", sa.Float(), nullable=True),
        sa.Column("patient_sex", sa.String(length=20), nullable=True),
        sa.Column("event_date", sa.String(length=50), nullable=True),
        sa.Column("report_quarter", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("report_id"),
    )
    op.create_index("ix_processed_reports_drug_name", "processed_reports", ["drug_name"])
    op.create_index("ix_processed_reports_report_quarter", "processed_reports", ["report_quarter"])

    op.create_table(
        "drug_event_pairs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("drug_name", sa.String(length=255), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drug_event_pairs_drug_name", "drug_event_pairs", ["drug_name"])
    op.create_index("ix_drug_event_pairs_event_name", "drug_event_pairs", ["event_name"])
    op.create_index("ix_drug_event_pairs_quarter", "drug_event_pairs", ["quarter"])

    op.create_table(
        "signals",
        sa.Column("signal_id", sa.String(length=50), nullable=False),
        sa.Column("drug_name", sa.String(length=255), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=False),
        sa.Column("supporting_report_count", sa.Integer(), nullable=False),
        sa.Column("prr", sa.Float(), nullable=False),
        sa.Column("ror", sa.Float(), nullable=True),
        sa.Column("trend_score", sa.Float(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("priority_level", sa.String(length=20), nullable=True),
        sa.Column("candidate_status", sa.String(length=30), nullable=False),
        sa.Column("dataset_version", sa.String(length=50), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("known_limitations", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("signal_id"),
    )
    op.create_index("ix_signals_drug_name", "signals", ["drug_name"])
    op.create_index("ix_signals_event_name", "signals", ["event_name"])
    op.create_index("ix_signals_dataset_version", "signals", ["dataset_version"])

    op.create_table(
        "signal_metrics",
        sa.Column("signal_id", sa.String(length=50), nullable=False),
        sa.Column("prr", sa.Float(), nullable=False),
        sa.Column("ror", sa.Float(), nullable=True),
        sa.Column("report_count", sa.Integer(), nullable=False),
        sa.Column("contingency_table", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("trend_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("chi_square", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("signal_id"),
    )

    op.create_table(
        "case_quality",
        sa.Column("signal_id", sa.String(length=50), nullable=False),
        sa.Column("total_reports", sa.Integer(), nullable=False),
        sa.Column("missing_age_count", sa.Integer(), nullable=False),
        sa.Column("missing_sex_count", sa.Integer(), nullable=False),
        sa.Column("missing_date_count", sa.Integer(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("quality_flags", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("indicators", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("signal_id"),
    )

    op.create_table(
        "duplicate_candidates",
        sa.Column("candidate_id", sa.String(length=50), nullable=False),
        sa.Column("signal_id", sa.String(length=50), nullable=True),
        sa.Column("report_id_a", sa.String(length=50), nullable=False),
        sa.Column("report_id_b", sa.String(length=50), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("drug_similarity", sa.Float(), nullable=True),
        sa.Column("event_similarity", sa.Float(), nullable=True),
        sa.Column("date_proximity_days", sa.Integer(), nullable=True),
        sa.Column("matched_fields", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("candidate_id"),
    )
    op.create_index("ix_duplicate_candidates_signal_id", "duplicate_candidates", ["signal_id"])

    op.create_table(
        "ai_summaries",
        sa.Column("summary_id", sa.String(length=50), nullable=False),
        sa.Column("signal_id", sa.String(length=50), nullable=False),
        sa.Column("why_flagged", sa.Text(), nullable=False),
        sa.Column("evidence_summary", sa.Text(), nullable=False),
        sa.Column("limitations", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("suggested_questions", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("summary_id"),
    )
    op.create_index("ix_ai_summaries_signal_id", "ai_summaries", ["signal_id"])

    op.create_table(
        "document_uploads",
        sa.Column("document_id", sa.String(length=50), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("signal_id", sa.String(length=50), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extracted_text_preview", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index("ix_document_uploads_signal_id", "document_uploads", ["signal_id"])

    op.create_table(
        "document_analysis",
        sa.Column("analysis_id", sa.String(length=50), nullable=False),
        sa.Column("document_id", sa.String(length=50), nullable=False),
        sa.Column("signal_id", sa.String(length=50), nullable=False),
        sa.Column("relevant_sections", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("existing_related_content", sa.Text(), nullable=True),
        sa.Column("potential_coverage_gap", sa.Text(), nullable=True),
        sa.Column("analysis_status", sa.String(length=30), nullable=False),
        sa.Column("human_review_required", sa.Boolean(), nullable=False),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("disclaimer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("analysis_id"),
    )
    op.create_index("ix_document_analysis_document_id", "document_analysis", ["document_id"])
    op.create_index("ix_document_analysis_signal_id", "document_analysis", ["signal_id"])


def downgrade() -> None:
    op.drop_index("ix_document_analysis_signal_id", table_name="document_analysis")
    op.drop_index("ix_document_analysis_document_id", table_name="document_analysis")
    op.drop_table("document_analysis")

    op.drop_index("ix_document_uploads_signal_id", table_name="document_uploads")
    op.drop_table("document_uploads")

    op.drop_index("ix_ai_summaries_signal_id", table_name="ai_summaries")
    op.drop_table("ai_summaries")

    op.drop_index("ix_duplicate_candidates_signal_id", table_name="duplicate_candidates")
    op.drop_table("duplicate_candidates")
    op.drop_table("case_quality")
    op.drop_table("signal_metrics")

    op.drop_index("ix_signals_dataset_version", table_name="signals")
    op.drop_index("ix_signals_event_name", table_name="signals")
    op.drop_index("ix_signals_drug_name", table_name="signals")
    op.drop_table("signals")

    op.drop_index("ix_drug_event_pairs_quarter", table_name="drug_event_pairs")
    op.drop_index("ix_drug_event_pairs_event_name", table_name="drug_event_pairs")
    op.drop_index("ix_drug_event_pairs_drug_name", table_name="drug_event_pairs")
    op.drop_table("drug_event_pairs")

    op.drop_index("ix_processed_reports_report_quarter", table_name="processed_reports")
    op.drop_index("ix_processed_reports_drug_name", table_name="processed_reports")
    op.drop_table("processed_reports")

    op.drop_index(
        "ix_faers_quarterly_metadata_quarter",
        table_name="faers_quarterly_metadata",
    )
    op.drop_table("faers_quarterly_metadata")
