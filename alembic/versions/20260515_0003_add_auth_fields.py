"""add auth fields

Revision ID: 20260515_0003
Revises: 20260515_0002
Create Date: 2026-05-15 00:00:02.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260515_0003"
down_revision: str | None = "20260515_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("hashed_password", sa.String(length=255), nullable=True))
    op.execute("UPDATE users SET username = split_part(email, '@', 1) WHERE username IS NULL")
    op.execute("UPDATE users SET hashed_password = 'not-set' WHERE hashed_password IS NULL")
    op.alter_column("users", "username", nullable=False)
    op.alter_column("users", "hashed_password", nullable=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_unique_constraint("uq_users_username", "users", ["username"])

    op.add_column("client_sessions", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_client_sessions_user_id_users", "client_sessions", "users", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_client_sessions_user_id_users", "client_sessions", type_="foreignkey")
    op.drop_column("client_sessions", "user_id")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "hashed_password")
    op.drop_column("users", "username")
