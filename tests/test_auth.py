from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_role, store_session_user
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.models import User
from app.routers.auth import safe_next_url, validate_login_form, validate_register_form


def test_password_hashing_verifies_and_rejects_wrong_password() -> None:
    password_hash = hash_password("client123")

    assert password_hash != "client123"
    assert verify_password("client123", password_hash) is True
    assert verify_password("wrong", password_hash) is False


def test_login_and_register_validation_helpers() -> None:
    assert validate_login_form("", "") == "Введите логин и пароль."
    assert validate_login_form("admin", "admin123") == ""
    assert validate_register_form("", "a@b.test", "Name", "secret1")
    assert validate_register_form("client", "client@test.local", "Client", "123") == "Пароль должен содержать минимум 6 символов."
    assert validate_register_form("client", "client@test.local", "Client", "client123") == ""
    assert safe_next_url("/client/dashboard") == "/client/dashboard"
    assert safe_next_url("https://example.com") == ""


def test_current_user_and_role_helper() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(
            username="manager",
            email="manager@test.local",
            full_name="Manager",
            role="manager",
            hashed_password=hash_password("manager123"),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        request = SimpleNamespace(session={})
        store_session_user(request, user)

        current_user = get_current_user(request, db)
        allowed_user = require_role(request, db, {"manager", "admin"})
        denied_response = require_role(request, db, {"admin"})

    assert current_user.username == "manager"
    assert allowed_user.username == "manager"
    assert getattr(denied_response, "status_code") == 303
