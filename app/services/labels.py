from app.models import Appeal


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


def role_label(value: str | None) -> str:
    return ROLE_LABELS.get(value or "", value or "Роль не указана")


def source_label(value: str | None) -> str:
    return SOURCE_LABELS.get(value or "", value or "Автоматический ответ")


def appeal_category_label(appeal: Appeal | None) -> str:
    if appeal is None:
        return "Другое"
    if appeal.category and appeal.category.name:
        return category_label(appeal.category.name)
    return category_label(appeal.request_category)


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
