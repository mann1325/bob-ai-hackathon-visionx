"""Add official FAERS outcome evidence to processed reports.

Revision ID: 20260918_0002
Revises: 20260915_0001
Create Date: 2026-09-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260918_0002"
down_revision: Union[str, None] = "20260915_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "processed_reports",
        sa.Column("seriousness", sa.String(length=20), nullable=False, server_default="Unknown"),
    )
    op.add_column(
        "processed_reports",
        sa.Column(
            "seriousness_codes",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.alter_column("processed_reports", "seriousness", server_default=None)
    op.alter_column("processed_reports", "seriousness_codes", server_default=None)


def downgrade() -> None:
    op.drop_column("processed_reports", "seriousness_codes")
    op.drop_column("processed_reports", "seriousness")