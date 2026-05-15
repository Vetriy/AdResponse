"""initial domain models

Revision ID: 20260515_0001
Revises:
Create Date: 2026-05-15 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260515_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "client_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("client_contact", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_session_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["client_session_id"], ["client_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "knowledge_base_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "appeals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("assigned_manager_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("emotional_tone", sa.String(length=50), nullable=True),
        sa.Column("request_category", sa.String(length=120), nullable=True),
        sa.Column("priority", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["assigned_manager_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender_type", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "generated_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appeal_id", sa.Integer(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["appeal_id"], ["appeals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "handover_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appeal_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["appeal_id"], ["appeals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sentiment_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("emotional_tone", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )


def downgrade() -> None:
    op.drop_table("sentiment_analyses")
    op.drop_table("handover_requests")
    op.drop_table("generated_responses")
    op.drop_table("messages")
    op.drop_table("appeals")
    op.drop_table("knowledge_base_items")
    op.drop_table("conversations")
    op.drop_index(op.f("ix_categories_slug"), table_name="categories")
    op.drop_table("categories")
    op.drop_table("client_sessions")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
