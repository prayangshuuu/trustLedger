"""Add legacy bank-rule flags to users (Inclusion Lift comparison only).

Revision ID: 0004_user_bank_flags
Revises: 0003_knowledge_chunks
Create Date: 2026-11-20 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_user_bank_flags"
down_revision: str | None = "0003_knowledge_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("has_bank_account", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("has_salary_slip", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("has_salary_slip")
        batch.drop_column("has_bank_account")
