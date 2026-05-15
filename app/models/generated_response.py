from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class GeneratedResponse(TimestampMixin, Base):
    __tablename__ = "generated_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    appeal_id: Mapped[int] = mapped_column(ForeignKey("appeals.id"), nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="local_llm", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)

    appeal: Mapped["Appeal"] = relationship(back_populates="generated_responses")
