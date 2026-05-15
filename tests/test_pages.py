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
