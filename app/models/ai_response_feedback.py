from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AiResponseFeedback(TimestampMixin, Base):
    __tablename__ = "ai_response_feedback"
    __table_args__ = (
        CheckConstraint("value IN ('like', 'dislike')", name="ck_ai_response_feedback_value"),
        UniqueConstraint("message_id", "client_user_id", name="uq_ai_response_feedback_message_client"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id"), nullable=False)
    client_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    value: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(120))
    custom_reason: Mapped[str | None] = mapped_column(Text)

    message: Mapped["Message"] = relationship(back_populates="ai_feedback")
    appeal: Mapped["Appeal"] = relationship(back_populates="ai_feedback")
    client: Mapped["User"] = relationship(back_populates="ai_response_feedback")
