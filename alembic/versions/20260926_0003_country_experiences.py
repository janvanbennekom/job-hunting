"""Country experience evidence table (Phase 3C.3A).

Revision ID: 20260926_0003
Revises: 20260926_0002
Create Date: 2026-09-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0003"
down_revision: Union[str, Sequence[str], None] = "20260926_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "country_experiences",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("country", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_document_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["profile_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_document_id",
            "country",
            name="uq_country_experiences_source_document_country",
        ),
    )


def downgrade() -> None:
    op.drop_table("country_experiences")
