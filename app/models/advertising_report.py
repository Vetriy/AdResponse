from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AdvertisingReport(TimestampMixin, Base):
    __tablename__ = "advertising_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    appeal_id: Mapped[int | None] = mapped_column(ForeignKey("appeals.id"))
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"))
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    client: Mapped["User"] = relationship(foreign_keys=[client_user_id], back_populates="advertising_reports")
    uploaded_by: Mapped["User"] = relationship(foreign_keys=[uploaded_by_user_id], back_populates="uploaded_reports")
    appeal: Mapped["Appeal | None"] = relationship(back_populates="advertising_reports")
    conversation: Mapped["Conversation | None"] = relationship(back_populates="advertising_reports")
