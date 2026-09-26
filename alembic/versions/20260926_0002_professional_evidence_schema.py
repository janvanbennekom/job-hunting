"""Professional evidence schema (Phase 3B).

Revision ID: 20260926_0002
Revises: 20260324_0001
Create Date: 2026-09-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0002"
down_revision: Union[str, Sequence[str], None] = "20260324_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "profile_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source_reference", sa.String(length=2048), nullable=True),
        sa.Column("version_label", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "professional_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("positioning_summary", sa.Text(), nullable=True),
        sa.Column("primary_cv_document_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["primary_cv_document_id"],
            ["profile_documents.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "professional_services",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["profile_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "capabilities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["profile_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_capabilities_code"),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_record_id", sa.String(length=64), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column("project_name", sa.String(length=1024), nullable=False),
        sa.Column("role", sa.String(length=512), nullable=True),
        sa.Column("beneficiary", sa.String(length=512), nullable=True),
        sa.Column("donor", sa.String(length=512), nullable=True),
        sa.Column("country", sa.String(length=255), nullable=True),
        sa.Column("period_text", sa.String(length=255), nullable=True),
        sa.Column("working_days", sa.Integer(), nullable=True),
        sa.Column("last_active_year", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("responsibilities", sa.Text(), nullable=True),
        sa.Column("tools_technologies_text", sa.Text(), nullable=True),
        sa.Column("web_link", sa.String(length=2048), nullable=True),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["profile_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["profile_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "language_capabilities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("language", sa.String(length=128), nullable=False),
        sa.Column("proficiency_text", sa.String(length=512), nullable=True),
        sa.Column("cefr_level", sa.String(length=16), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["profile_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assignment_capabilities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("assignment_id", sa.String(length=36), nullable=False),
        sa.Column("capability_id", sa.String(length=36), nullable=False),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id"],
            ["capabilities.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["profile_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            "capability_id",
            name="uq_assignment_capabilities_assignment_capability",
        ),
    )
    op.create_index(
        op.f("ix_assignment_capabilities_assignment_id"),
        "assignment_capabilities",
        ["assignment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_capabilities_capability_id"),
        "assignment_capabilities",
        ["capability_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_assignment_capabilities_capability_id"),
        table_name="assignment_capabilities",
    )
    op.drop_index(
        op.f("ix_assignment_capabilities_assignment_id"),
        table_name="assignment_capabilities",
    )
    op.drop_table("assignment_capabilities")
    op.drop_table("language_capabilities")
    op.drop_table("skills")
    op.drop_table("assignments")
    op.drop_table("capabilities")
    op.drop_table("professional_services")
    op.drop_table("professional_profiles")
    op.drop_table("profile_documents")
