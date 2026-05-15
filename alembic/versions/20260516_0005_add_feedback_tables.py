"""add appeal and ai response feedback

Revision ID: 20260516_0005
Revises: 20260515_0004
Create Date: 2026-05-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0005"
down_revision: str | None = "20260515_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "appeal_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appeal_id", sa.Integer(), nullable=False),
        sa.Column("client_user_id", sa.Integer(), nullable=False),
        sa.Column("manager_user_id", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_appeal_feedback_rating_range"),
        sa.ForeignKeyConstraint(["appeal_id"], ["appeals.id"]),
        sa.ForeignKeyConstraint(["client_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["manager_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appeal_id", "client_user_id", name="uq_appeal_feedback_appeal_client"),
    )
    op.create_table(
        "ai_response_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("appeal_id", sa.Integer(), nullable=False),
        sa.Column("client_user_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column("custom_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("value IN ('like', 'dislike')", name="ck_ai_response_feedback_value"),
        sa.ForeignKeyConstraint(["appeal_id"], ["appeals.id"]),
        sa.ForeignKeyConstraint(["client_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "client_user_id", name="uq_ai_response_feedback_message_client"),
    )


def downgrade() -> None:
    op.drop_table("ai_response_feedback")
    op.drop_table("appeal_feedback")
