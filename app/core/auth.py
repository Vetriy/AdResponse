from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User

ROLE_DASHBOARDS = {
    "client": "/client/dashboard",
    "manager": "/manager/dashboard",
    "admin": "/admin/dashboard",
}


def session_user(request: Request) -> dict | None:
    return request.session.get("user")


def store_session_user(request: Request, user: User) -> None:
    request.session["user"] = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


def clear_session(request: Request) -> None:
    request.session.clear()


def get_current_user(request: Request, db: Session) -> User | None:
    user_data = session_user(request)
    if not user_data:
        return None
    user = db.get(User, int(user_data["id"]))
    if user is None or not user.is_active:
        clear_session(request)
        return None
    return user


def login_redirect(request: Request) -> RedirectResponse:
    next_url = quote(str(request.url.path))
    return RedirectResponse(f"/login?next={next_url}", status_code=303)


def access_denied(request: Request) -> RedirectResponse:
    user = session_user(request)
    if user:
        return RedirectResponse(ROLE_DASHBOARDS.get(user["role"], "/"), status_code=303)
    return login_redirect(request)


def require_auth(request: Request, db: Session) -> User | RedirectResponse:
    user = get_current_user(request, db)
    return user if user else login_redirect(request)


def require_role(request: Request, db: Session, roles: set[str]) -> User | RedirectResponse:
    user = get_current_user(request, db)
    if user is None:
        return login_redirect(request)
    if user.role not in roles:
        return access_denied(request)
    return user


def find_user_for_login(db: Session, login: str) -> User | None:
    normalized = login.strip().lower()
    return db.scalar(
        select(User).where(
            (User.username == normalized) | (User.email == normalized),
            User.is_active.is_(True),
        )
    )
