from fastapi.testclient import TestClient

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
