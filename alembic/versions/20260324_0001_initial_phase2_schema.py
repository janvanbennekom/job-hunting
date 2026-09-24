"""Initial Phase 2 schema for JobHunter core entities.

Revision ID: 20260324_0001
Revises:
Create Date: 2026-03-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260324_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("organisation", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("organisation", sa.String(length=512), nullable=True),
        sa.Column("location", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("expected_start_date", sa.Date(), nullable=True),
        sa.Column("opportunity_type", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("eligibility_status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "raw_opportunities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("source_reference", sa.String(length=512), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_title", sa.String(length=1024), nullable=True),
        sa.Column("raw_organisation", sa.String(length=512), nullable=True),
        sa.Column("raw_location", sa.String(length=512), nullable=True),
        sa.Column("raw_deadline", sa.String(length=255), nullable=True),
        sa.Column("raw_description", sa.Text(), nullable=True),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["job_sources.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_raw_opportunities_source_id"),
        "raw_opportunities",
        ["source_id"],
        unique=False,
    )
    op.create_table(
        "opportunity_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("opportunity_id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("source_reference", sa.String(length=512), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("original_url", sa.String(length=2048), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["job_sources.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "opportunity_id",
            "source_id",
            name="uq_opportunity_sources_opportunity_source",
        ),
    )
    op.create_index(
        op.f("ix_opportunity_sources_opportunity_id"),
        "opportunity_sources",
        ["opportunity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_opportunity_sources_source_id"),
        "opportunity_sources",
        ["source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_opportunity_sources_source_id"), table_name="opportunity_sources"
    )
    op.drop_index(
        op.f("ix_opportunity_sources_opportunity_id"),
        table_name="opportunity_sources",
    )
    op.drop_table("opportunity_sources")
    op.drop_index(op.f("ix_raw_opportunities_source_id"), table_name="raw_opportunities")
    op.drop_table("raw_opportunities")
    op.drop_table("opportunities")
    op.drop_table("job_sources")
