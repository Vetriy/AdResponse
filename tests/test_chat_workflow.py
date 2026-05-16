from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models import Category, ClientSession, Conversation, Message, User
from app.services.chat_workflow import generate_auto_reply_for_conversation, process_client_message


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


def test_disabled_auto_reply_saves_client_message_without_system_answer() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Category(slug="other", name="other", description="", is_active=True))
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

        conversation, _, _, appeal, _, _ = process_client_message(db, "Первое сообщение", user=user)
        appeal.auto_reply_enabled = False
        db.commit()

        _, client_message, system_message, updated_appeal, questions, handover = process_client_message(
            db,
            "Новое уточнение клиента",
            conversation_id=conversation.id,
            user=user,
        )
        messages = list(db.query(Message).filter(Message.conversation_id == conversation.id))

    assert client_message.content == "Новое уточнение клиента"
    assert system_message is None
    assert updated_appeal.status == "needs_manager"
    assert questions == []
    assert handover is True
    assert [message.sender_type for message in messages].count("system") == 1


def test_report_thread_auto_reply_can_be_enabled_or_disabled() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Category(slug="other", name="other", description="", is_active=True))
        user = User(
            username="client",
            email="client@test.local",
            full_name="Client",
            role="client",
            client_type="active_client",
            hashed_password=hash_password("client123"),
            is_active=True,
        )
        conversation = Conversation(
            client_session=ClientSession(user=user),
            title="Отчеты",
            conversation_type="report_thread",
            auto_reply_enabled=True,
        )
        db.add_all([user, conversation])
        db.commit()

        enabled_reply = generate_auto_reply_for_conversation(db, conversation, "Что значит мало заявок?", report_context="Отчет за май")
        conversation.auto_reply_enabled = False
        disabled_reply = generate_auto_reply_for_conversation(db, conversation, "Еще вопрос", report_context="Отчет за май")

    assert enabled_reply is not None
    assert enabled_reply.sender_type == "system"
    assert disabled_reply is None
    assert conversation.status == "needs_manager"
