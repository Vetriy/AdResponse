"""add conversation auto reply flag

Revision ID: 20260516_0007
Revises: 20260516_0006
Create Date: 2026-05-16 00:00:07.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0007"
down_revision: str | None = "20260516_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("auto_reply_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("conversations", "auto_reply_enabled")
