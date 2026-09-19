"""Add current human review records for signals.

Revision ID: 20260918_0003
Revises: 20260918_0002
Create Date: 2026-09-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260918_0003"
down_revision: Union[str, None] = "20260918_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signal_reviews",
        sa.Column("review_id", sa.String(length=50), nullable=False),
        sa.Column("signal_id", sa.String(length=50), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="not_started"),
        sa.Column("evidence_checklist", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("reviewer_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewer_conclusion", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.signal_id"]),
        sa.PrimaryKeyConstraint("review_id"),
        sa.UniqueConstraint("signal_id"),
    )
    op.create_index("ix_signal_reviews_signal_id", "signal_reviews", ["signal_id"])
    op.alter_column("signal_reviews", "review_status", server_default=None)
    op.alter_column("signal_reviews", "evidence_checklist", server_default=None)
    op.alter_column("signal_reviews", "reviewer_notes", server_default=None)
    op.alter_column("signal_reviews", "reviewer_conclusion", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_signal_reviews_signal_id", table_name="signal_reviews")
    op.drop_table("signal_reviews")