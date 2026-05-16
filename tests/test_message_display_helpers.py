from datetime import date, datetime

from app.models import Appeal, ClientSession, Conversation, Message, User
from app.services.labels import message_author_name, message_date_label, message_role_label


def test_message_display_labels_follow_chat_rules() -> None:
    client = User(id=1, username="client", email="client@test.local", full_name="Анна Клиент", role="client", hashed_password="x")
    manager = User(id=2, username="manager", email="manager@test.local", full_name="Мария Менеджер", role="manager", hashed_password="x")
    conversation = Conversation(client_session=ClientSession(user=client))
    appeal = Appeal(conversation=conversation, assigned_manager=manager)

    client_message = Message(sender_type="client", content="Здравствуйте")
    manager_message = Message(sender_type="manager", content="Добрый день")
    system_message = Message(sender_type="system", content="Автоответ")

    assert message_author_name(client_message, conversation, appeal) == "Анна Клиент"
    assert message_role_label(client_message) == ""
    assert message_author_name(manager_message, conversation, appeal) == "Мария Менеджер"
    assert message_role_label(manager_message) == "Менеджер"
    assert message_author_name(system_message, conversation, appeal) == ""
    assert message_role_label(system_message) == ""


def test_message_author_prefers_stored_sender_display_name() -> None:
    message = Message(sender_type="manager", sender_display_name="Елена Иванова", content="Ответ")

    assert message_author_name(message) == "Елена Иванова"
    assert message_role_label(message) == "Менеджер"


def test_message_date_label_is_telegram_like() -> None:
    today = date(2026, 5, 16)

    assert message_date_label(datetime(2026, 5, 16, 10, 30), today=today) == "Сегодня"
    assert message_date_label(datetime(2026, 5, 15, 10, 30), today=today) == "Вчера"
    assert message_date_label(datetime(2026, 5, 14, 10, 30), today=today) == "14.05.2026"
