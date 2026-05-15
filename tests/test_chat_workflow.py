from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models import Category, User
from app.services.chat_workflow import process_client_message


def test_client_message_without_conversation_creates_separate_appeals() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Category(slug="service-cost", name="service cost", description="", is_active=True))
        user = User(
            username="client",
            email="client@test.local",
            full_name="Client",
            role="client",
            hashed_password=hash_password("client123"),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        first_conversation, _, _, first_appeal, _, _ = process_client_message(db, "Сколько стоит реклама?", user=user)
        second_conversation, _, _, second_appeal, _, _ = process_client_message(db, "Сколько стоит запуск?", user=user)

        assert first_conversation.id != second_conversation.id
        assert first_appeal.id != second_appeal.id


def test_existing_conversation_continues_selected_appeal() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Category(slug="service-cost", name="service cost", description="", is_active=True))
        user = User(
            username="client",
            email="client@test.local",
            full_name="Client",
            role="client",
            hashed_password=hash_password("client123"),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        conversation, _, _, appeal, _, _ = process_client_message(db, "Сколько стоит реклама?", user=user)
        same_conversation, _, _, same_appeal, _, _ = process_client_message(
            db,
            "Регион Москва",
            conversation_id=conversation.id,
            user=user,
        )

        assert same_conversation.id == conversation.id
        assert same_appeal.id == appeal.id
