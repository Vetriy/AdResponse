"""add knowledge item emotional tone

Revision ID: 20260515_0002
Revises: 20260515_0001
Create Date: 2026-05-15 00:00:01.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260515_0002"
down_revision: str | None = "20260515_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "knowledge_base_items",
        sa.Column("emotional_tone", sa.String(length=50), server_default="any", nullable=False),
    )
    op.alter_column("knowledge_base_items", "emotional_tone", server_default=None)


def downgrade() -> None:
    op.drop_column("knowledge_base_items", "emotional_tone")
