from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.core.auth import ROLE_DASHBOARDS, clear_session, find_user_for_login, store_session_user
from app.core.security import hash_password, verify_password
from app.core.templates import create_templates
from app.db.session import SessionLocal, database_error_message, get_engine
from app.models import User

templates = create_templates()
router = APIRouter(tags=["auth"])


async def read_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode()
    return {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}


def redirect_to(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def safe_next_url(value: str) -> str:
    if value.startswith("/") and not value.startswith("//"):
        return value
    return ""


def validate_login_form(login: str, password: str) -> str:
    if not login.strip() or not password:
        return "Введите логин и пароль."
    return ""


def validate_register_form(username: str, email: str, full_name: str, password: str) -> str:
    if not username.strip() or not email.strip() or not full_name.strip() or not password:
        return "Заполните все поля."
    if len(password) < 6:
        return "Пароль должен содержать минимум 6 символов."
    return ""


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"page_title": "Вход", "active_page": "login", "error": "", "next": next},
    )


@router.post("/login")
async def login(request: Request):
    form = await read_form(request)
    login_value = form.get("login", "")
    password = form.get("password", "")
    next_url = safe_next_url(form.get("next", ""))
    error = validate_login_form(login_value, password)
    if error:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"page_title": "Вход", "active_page": "login", "error": error, "next": next_url},
        )

    try:
        get_engine()
        db = SessionLocal()
    except Exception as db_error:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"page_title": "Вход", "active_page": "login", "error": database_error_message(db_error), "next": next_url},
        )

    try:
        user = find_user_for_login(db, login_value)
        if user is None or not verify_password(password, user.hashed_password):
            return templates.TemplateResponse(
                request,
                "auth/login.html",
                {"page_title": "Вход", "active_page": "login", "error": "Неверный логин или пароль.", "next": next_url},
            )
        store_session_user(request, user)
        return redirect_to(next_url or ROLE_DASHBOARDS.get(user.role, "/"))
    finally:
        db.close()


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    clear_session(request)
    return redirect_to("/login")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "auth/register.html",
        {"page_title": "Регистрация", "active_page": "register", "error": "", "form": {}},
    )


@router.post("/register")
async def register(request: Request):
    form = await read_form(request)
    username = form.get("username", "").strip().lower()
    email = form.get("email", "").strip().lower()
    full_name = form.get("full_name", "").strip()
    password = form.get("password", "")
    error = validate_register_form(username, email, full_name, password)
    if error:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {"page_title": "Регистрация", "active_page": "register", "error": error, "form": form},
        )

    get_engine()
    db = SessionLocal()
    try:
        exists = db.scalar(select(User).where((User.username == username) | (User.email == email)))
        if exists:
            return templates.TemplateResponse(
                request,
                "auth/register.html",
                {"page_title": "Регистрация", "active_page": "register", "error": "Пользователь уже существует.", "form": form},
            )
        user = User(username=username, email=email, full_name=full_name, role="client", hashed_password=hash_password(password), is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        store_session_user(request, user)
        return redirect_to("/client/dashboard")
    finally:
        db.close()
