"""add client types, auto replies, report threads and read markers

Revision ID: 20260516_0006
Revises: 20260516_0005
Create Date: 2026-05-16 00:00:06.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0006"
down_revision: str | None = "20260516_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("client_type", sa.String(length=50), server_default="potential_client", nullable=False),
    )
    op.add_column(
        "appeals",
        sa.Column("auto_reply_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "conversations",
        sa.Column("conversation_type", sa.String(length=50), server_default="appeal", nullable=False),
    )
    op.add_column("conversations", sa.Column("client_last_read_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("conversations", sa.Column("manager_last_read_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("advertising_reports", sa.Column("conversation_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_advertising_reports_conversation_id_conversations",
        "advertising_reports",
        "conversations",
        ["conversation_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_advertising_reports_conversation_id_conversations", "advertising_reports", type_="foreignkey")
    op.drop_column("advertising_reports", "conversation_id")
    op.drop_column("conversations", "manager_last_read_at")
    op.drop_column("conversations", "client_last_read_at")
    op.drop_column("conversations", "conversation_type")
    op.drop_column("appeals", "auto_reply_enabled")
    op.drop_column("users", "client_type")
