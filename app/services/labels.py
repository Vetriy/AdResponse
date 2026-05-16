from datetime import date, datetime

from app.models import Appeal, Conversation, Message
from app.models.generated_response import GeneratedResponse
from app.services.sentiment import analyze_sentiment


STATUS_LABELS = {
    "new": "Новое",
    "auto_answered": "Автоответ отправлен",
    "auto_response": "Автоответ отправлен",
    "needs_clarification": "Требуется уточнение",
    "handover_requested": "Запрошен менеджер",
    "needs_manager": "Требуется менеджер",
    "assigned_to_manager": "В работе у менеджера",
    "accepted": "Передано менеджеру",
    "manager_answered": "Менеджер ответил",
    "closed": "Закрыто",
}

TONE_LABELS = {
    "neutral": "Нейтральный",
    "interested": "Заинтересованный",
    "anxious": "Тревожный",
    "disappointed": "Недовольный",
    "irritated": "Раздраженный",
    "negative": "Негативный",
    "any": "Любой",
}

CATEGORY_LABELS = {
    "service cost": "Стоимость услуг",
    "campaign launch": "Запуск рекламной кампании",
    "advertising campaign launch": "Запуск рекламной кампании",
    "low number of leads": "Мало заявок",
    "dissatisfaction with campaign results": "Недовольство результатами",
    "limited budget": "Ограниченный бюджет",
    "consultation request": "Запрос консультации",
    "request for consultation": "Запрос консультации",
    "contact manager request": "Связь с менеджером",
    "request to contact manager": "Связь с менеджером",
    "general question": "Общий вопрос",
    "other": "Другое",
}

SENDER_LABELS = {
    "client": "Клиент",
    "system": "Онлайн-помощник",
    "manager": "Менеджер",
}

ROLE_LABELS = {
    "admin": "Администратор",
    "manager": "Менеджер",
    "client": "Клиент",
}

CLIENT_TYPE_LABELS = {
    "active_client": "Действующий клиент",
    "potential_client": "Потенциальный клиент",
}

CLIENT_TYPE_COMPACT_LABELS = {
    "active_client": "Действ.",
    "potential_client": "Пот.",
}

SOURCE_LABELS = {
    "local_rules": "Автоматический ответ",
    "local_llama_cpp": "Локальная языковая модель",
    "local_llm": "Локальная языковая модель",
}


def status_label(value: str | None) -> str:
    return STATUS_LABELS.get(value or "", value or "Не указан")


def tone_label(value: str | None) -> str:
    return TONE_LABELS.get(value or "", value or "Не указан")


def category_label(value: str | None) -> str:
    return CATEGORY_LABELS.get(value or "", value or "Другое")


def sender_label(value: str | None) -> str:
    return SENDER_LABELS.get(value or "", value or "Сообщение")


def message_author_name(message: Message, conversation: Conversation | None = None, appeal: Appeal | None = None) -> str:
    if message.sender_type == "system":
        return ""
    if message.sender_display_name:
        return message.sender_display_name
    if message.sender_type == "manager":
        if appeal and appeal.assigned_manager and appeal.assigned_manager.full_name:
            return appeal.assigned_manager.full_name
        return "Менеджер агентства"

    session = conversation.client_session if conversation else None
    user = session.user if session else None
    if user:
        return user.full_name or user.username or user.email or f"Клиент №{user.id}"
    if session:
        return session.client_name or session.client_contact or f"Клиент №{session.id}"
    return "Клиент"


def message_role_label(message: Message) -> str:
    if message.sender_type == "manager":
        return "Менеджер"
    return ""


def message_date_label(value: datetime | None, today: date | None = None) -> str:
    if value is None:
        return ""
    current_day = today or datetime.now(value.tzinfo).date()
    message_day = value.date()
    if message_day == current_day:
        return "Сегодня"
    if (current_day - message_day).days == 1:
        return "Вчера"
    return value.strftime("%d.%m.%Y")


def role_label(value: str | None) -> str:
    return ROLE_LABELS.get(value or "", value or "Роль не указана")


def client_type_label(value: str | None) -> str:
    return CLIENT_TYPE_LABELS.get(value or "", "Потенциальный клиент")


def compact_client_type_label(value: str | None) -> str:
    return CLIENT_TYPE_COMPACT_LABELS.get(value or "", "Пот.")


def source_label(value: str | None) -> str:
    return SOURCE_LABELS.get(value or "", value or "Автоматический ответ")


def latest_generated_response(responses: list[GeneratedResponse]) -> GeneratedResponse | None:
    if not responses:
        return None
    return max(responses, key=lambda response: (response.created_at or datetime.min, response.id or 0))


def appeal_category_label(appeal: Appeal | None) -> str:
    if appeal is None:
        return "Другое"
    if appeal.category and appeal.category.name:
        return category_label(appeal.category.name)
    return category_label(appeal.request_category)


def current_appeal_tone(appeal: Appeal | None) -> str:
    if appeal is None or appeal.conversation is None:
        return "neutral"
    client_parts = [
        message.content
        for message in appeal.conversation.messages
        if message.sender_type == "client" and message.content
    ]
    if not client_parts:
        return appeal.emotional_tone or "neutral"
    return analyze_sentiment("\n".join(client_parts)).emotional_tone


def client_identifier(appeal: Appeal | None) -> str:
    if appeal is None or appeal.conversation is None or appeal.conversation.client_session is None:
        return "Клиент"

    session = appeal.conversation.client_session
    user = session.user
    if user:
        if user.full_name:
            return user.full_name
        if user.username:
            return user.username
        if user.email:
            return user.email
        return f"Клиент №{user.id}"

    if session.client_name:
        return session.client_name
    if session.client_contact:
        return session.client_contact
    return f"Клиент №{session.id}"
