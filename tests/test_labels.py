from types import SimpleNamespace

from app.services.labels import category_label, client_identifier, status_label, tone_label


def test_domain_labels_are_displayed_in_russian() -> None:
    assert status_label("auto_answered") == "Автоответ отправлен"
    assert status_label("assigned_to_manager") == "Передано менеджеру"
    assert tone_label("irritated") == "Раздраженный"
    assert tone_label("any") == "Любой"
    assert category_label("service cost") == "Стоимость услуг"
    assert category_label("contact manager request") == "Связь с менеджером"


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

    assert client_identifier(appeal) == "Клиент #8"
