from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Appeal(TimestampMixin, Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), unique=True, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    assigned_manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    emotional_tone: Mapped[str | None] = mapped_column(String(50))
    request_category: Mapped[str | None] = mapped_column(String(120))
    priority: Mapped[str] = mapped_column(String(30), default="normal", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    conversation: Mapped["Conversation"] = relationship(back_populates="appeal")
    category: Mapped["Category | None"] = relationship(back_populates="appeals")
    assigned_manager: Mapped["User | None"] = relationship(back_populates="assigned_appeals")
    generated_responses: Mapped[list["GeneratedResponse"]] = relationship(
        back_populates="appeal",
        cascade="all, delete-orphan",
    )
    handover_requests: Mapped[list["HandoverRequest"]] = relationship(
        back_populates="appeal",
        cascade="all, delete-orphan",
    )
    advertising_reports: Mapped[list["AdvertisingReport"]] = relationship(back_populates="appeal")
    feedback: Mapped[list["AppealFeedback"]] = relationship(
        back_populates="appeal",
        cascade="all, delete-orphan",
    )
    ai_feedback: Mapped[list["AiResponseFeedback"]] = relationship(
        back_populates="appeal",
        cascade="all, delete-orphan",
    )
