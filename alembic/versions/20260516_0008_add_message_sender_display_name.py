"""add message sender display name

Revision ID: 20260516_0008
Revises: 20260516_0007
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260516_0008"
down_revision = "20260516_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("sender_display_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "sender_display_name")
