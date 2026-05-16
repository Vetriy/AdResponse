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
