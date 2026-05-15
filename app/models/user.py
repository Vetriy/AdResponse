from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="manager", nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assigned_appeals: Mapped[list["Appeal"]] = relationship(
        back_populates="assigned_manager",
        cascade="save-update, merge",
    )
    client_sessions: Mapped[list["ClientSession"]] = relationship(back_populates="user")
    message_attachments: Mapped[list["MessageAttachment"]] = relationship(back_populates="uploaded_by")
    advertising_reports: Mapped[list["AdvertisingReport"]] = relationship(
        foreign_keys="AdvertisingReport.client_user_id",
        back_populates="client",
    )
    uploaded_reports: Mapped[list["AdvertisingReport"]] = relationship(
        foreign_keys="AdvertisingReport.uploaded_by_user_id",
        back_populates="uploaded_by",
    )
