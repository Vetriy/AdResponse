from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AppealFeedback(TimestampMixin, Base):
    __tablename__ = "appeal_feedback"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_appeal_feedback_rating_range"),
        UniqueConstraint("appeal_id", "client_user_id", name="uq_appeal_feedback_appeal_client"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id"), nullable=False)
    client_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    manager_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    appeal: Mapped["Appeal"] = relationship(back_populates="feedback")
    client: Mapped["User"] = relationship(foreign_keys=[client_user_id], back_populates="appeal_feedback")
    manager: Mapped["User | None"] = relationship(foreign_keys=[manager_user_id], back_populates="manager_feedback")
