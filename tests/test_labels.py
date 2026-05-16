from types import SimpleNamespace

from app.services.labels import (
    category_label,
    client_identifier,
    client_type_label,
    compact_client_type_label,
    current_appeal_tone,
    role_label,
    source_label,
    status_label,
    tone_label,
)


def test_domain_labels_are_displayed_in_russian() -> None:
    assert status_label("auto_answered") == "Автоответ отправлен"
    assert status_label("assigned_to_manager") == "В работе у менеджера"
    assert tone_label("irritated") == "Раздраженный"
    assert tone_label("any") == "Любой"
    assert category_label("service cost") == "Стоимость услуг"
    assert category_label("contact manager request") == "Связь с менеджером"
    assert role_label("admin") == "Администратор"
    assert role_label("manager") == "Менеджер"
    assert role_label("client") == "Клиент"
    assert source_label("local_rules") == "Автоматический ответ"
    assert source_label("local_llama_cpp") == "Локальная языковая модель"
    assert client_type_label("active_client") == "Действующий клиент"
    assert compact_client_type_label("active_client") == "Действ."
    assert compact_client_type_label("potential_client") == "Пот."


def test_client_identifier_prefers_human_account_fields() -> None:
    appeal = SimpleNamespace(
        conversation=SimpleNamespace(
            client_session=SimpleNamespace(
                id=8,
                client_name=None,
                client_contact=None,
                user=SimpleNamespace(id=3, full_name="Анна Иванова", username="anna", email="anna@test.local"),
            )
        )
    )

    assert client_identifier(appeal) == "Анна Иванова"


def test_client_identifier_falls_back_to_session_id() -> None:
    appeal = SimpleNamespace(
        conversation=SimpleNamespace(
            client_session=SimpleNamespace(id=8, client_name=None, client_contact=None, user=None)
        )
    )

    assert client_identifier(appeal) == "Клиент №8"


def test_current_appeal_tone_uses_client_dialogue_context() -> None:
    appeal = SimpleNamespace(
        emotional_tone="neutral",
        conversation=SimpleNamespace(
            messages=[
                SimpleNamespace(sender_type="client", content="Добрый день"),
                SimpleNamespace(sender_type="manager", content="Ответ менеджера"),
                SimpleNamespace(sender_type="client", content="Мы разочарованы, ожидали лучше"),
            ]
        ),
    )

    assert current_appeal_tone(appeal) == "disappointed"
