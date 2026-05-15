from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ClientSession(TimestampMixin, Base):
    __tablename__ = "client_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    client_name: Mapped[str | None] = mapped_column(String(255))
    client_contact: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(100), default="website", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="client_session",
        cascade="all, delete-orphan",
    )
    user: Mapped["User | None"] = relationship(back_populates="client_sessions")
