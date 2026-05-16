from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_session_id: Mapped[int] = mapped_column(ForeignKey("client_sessions.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    conversation_type: Mapped[str] = mapped_column(String(50), default="appeal", nullable=False)
    client_last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manager_last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    client_session: Mapped["ClientSession"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    appeal: Mapped["Appeal | None"] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        uselist=False,
    )
    advertising_reports: Mapped[list["AdvertisingReport"]] = relationship(back_populates="conversation")
