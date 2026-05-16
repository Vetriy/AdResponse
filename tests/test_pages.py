from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app


client = TestClient(app)


def test_home_page_loads() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "AdResponse" in response.text


def test_placeholder_pages_load() -> None:
    for path in ("/chat/", "/manager/", "/admin/knowledge-base"):
        response = client.get(path)

        assert response.status_code == 200


def test_protected_routes_redirect_to_login() -> None:
    for path in ("/client/dashboard", "/manager/dashboard", "/admin/users"):
        response = client.get(path, follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"].startswith("/login")


def test_auth_pages_load() -> None:
    for path in ("/login", "/register"):
        response = client.get(path)

        assert response.status_code == 200


def test_client_templates_do_not_show_emotional_tone() -> None:
    for template in ("app/templates/chat/index.html", "app/templates/client/dashboard.html", "app/templates/client/appeal_detail.html"):
        text = Path(template).read_text()
        assert "data-chat-tone" not in text
        assert "<th>Тон</th>" not in text


def test_client_auto_reply_off_notice_is_static_not_js_bubble() -> None:
    assert "Автоответы в этом обращении выключены. Менеджер ответит вручную." in Path("app/templates/client/appeal_detail.html").read_text()
    assert "Автоответы по этому обращению выключены" not in Path("app/static/js/main.js").read_text()


def test_manager_clients_template_limits_report_action_to_active_clients() -> None:
    text = Path("app/templates/manager/clients.html").read_text()
    assert 'row.client.client_type == "active_client"' in text
    assert "data-autosubmit" in text
    assert "Сохранить</button>" not in text
    assert "data-table--clients" in text
    assert "Действия" in text
    assert "manager-client-actions" in text
    assert "compact_client_type_label" in text
    assert "client_type_label(row.client.client_type)" in text


def test_admin_users_search_uses_pastel_placeholder() -> None:
    text = Path("app/templates/admin/users.html").read_text()

    assert "Поиск по логину, email или имени" in text
    assert "pastel-search" in text


def test_admin_appeal_views_do_not_duplicate_manager_rating_block() -> None:
    appeal_detail = Path("app/templates/manager/appeal_detail.html").read_text()
    manager_dashboard = Path("app/templates/manager/dashboard.html").read_text()
    admin_dashboard = Path("app/templates/admin/dashboard.html").read_text()

    assert "Рейтинг менеджера" not in appeal_detail
    assert 'current_user.role == "manager"' in manager_dashboard
    assert "Рейтинг менеджеров" in admin_dashboard
    assert "Средняя оценка менеджеров" in admin_dashboard
    assert "Оцененных обращений" in admin_dashboard


def test_manager_templates_show_tone_summary_only_outside_client_views() -> None:
    manager_dashboard = Path("app/templates/manager/dashboard.html").read_text()
    manager_detail = Path("app/templates/manager/appeal_detail.html").read_text()
    client_detail = Path("app/templates/client/appeal_detail.html").read_text()

    assert "Эмоциональный тон:" not in manager_dashboard
    assert "tone-{{ display_tone }}" in manager_dashboard
    assert "tone_label(display_tone)" in manager_dashboard
    assert "Эмоциональный тон" in manager_detail
    assert "Текущий тон клиента" not in manager_dashboard
    assert "Текущий тон клиента" not in manager_detail
    assert "Текущий тон клиента" not in client_detail
