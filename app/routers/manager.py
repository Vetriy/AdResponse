from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import login_redirect, require_role
from app.core.templates import create_templates
from app.db.session import SessionLocal, database_error_message, get_engine
from app.models import Appeal, Category, ClientSession, Conversation, Message, User

templates = create_templates()
router = APIRouter(prefix="/manager", tags=["manager dashboard"])

APPEAL_STATUSES = (
    "new",
    "auto_answered",
    "needs_clarification",
    "handover_requested",
    "needs_manager",
    "assigned_to_manager",
    "manager_answered",
    "closed",
)
EMOTIONAL_TONES = ("neutral", "interested", "anxious", "disappointed", "irritated", "negative")
PLACEHOLDER_MANAGER_EMAIL = "manager@example.local"


def redirect_to(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def open_db():
    get_engine()
    return SessionLocal()


async def read_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode()
    return {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}


def get_or_create_placeholder_manager(db) -> User:
    manager = db.scalar(select(User).where(User.email == PLACEHOLDER_MANAGER_EMAIL))
    if manager is None:
        manager = User(
            username="manager-placeholder",
            email=PLACEHOLDER_MANAGER_EMAIL,
            full_name="Дежурный менеджер",
            role="manager",
            hashed_password="not-set",
            is_active=True,
        )
        db.add(manager)
        db.flush()
    return manager


@router.get("/", response_class=HTMLResponse)
async def manager_dashboard(
    request: Request,
    status: str = "",
    category: str = "",
    tone: str = "",
) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    try:
        db = open_db()
    except Exception as error:
        return templates.TemplateResponse(
            request,
            "manager/dashboard.html",
            {
                "page_title": "Панель менеджера",
                "active_page": "manager",
                "appeals": [],
                "categories": [],
                "statuses": APPEAL_STATUSES,
                "tones": EMOTIONAL_TONES,
                "filters": {"status": status, "category": category, "tone": tone},
                "metrics": {"new": 0, "needs_clarification": 0, "needs_manager": 0},
                "db_error": database_error_message(error),
            },
        )

    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        categories = list(db.scalars(select(Category).order_by(Category.name.asc())))
        all_appeals = list(db.scalars(select(Appeal)))
        metrics = {
            "new": sum(1 for appeal in all_appeals if appeal.status == "new"),
            "needs_clarification": sum(1 for appeal in all_appeals if appeal.status == "needs_clarification"),
            "needs_manager": sum(1 for appeal in all_appeals if appeal.status == "needs_manager"),
        }

        statement = (
            select(Appeal)
            .options(
                selectinload(Appeal.category),
                selectinload(Appeal.assigned_manager),
                selectinload(Appeal.conversation).selectinload(Conversation.messages),
                selectinload(Appeal.conversation).selectinload(Conversation.client_session).selectinload(ClientSession.user),
            )
            .order_by(Appeal.created_at.desc())
        )
        if current_user.role == "manager":
            statement = statement.where((Appeal.assigned_manager_id == current_user.id) | (Appeal.assigned_manager_id.is_(None)))
        if status:
            statement = statement.where(Appeal.status == status)
        if category and category.isdigit():
            statement = statement.where(Appeal.category_id == int(category))
        if tone:
            statement = statement.where(Appeal.emotional_tone == tone)

        appeals = list(db.scalars(statement))
        return templates.TemplateResponse(
            request,
            "manager/dashboard.html",
            {
                "page_title": "Панель менеджера",
                "active_page": "manager",
                "appeals": appeals,
                "categories": categories,
                "statuses": APPEAL_STATUSES,
                "tones": EMOTIONAL_TONES,
                "filters": {"status": status, "category": category, "tone": tone},
                "metrics": metrics,
                "db_error": None,
            },
        )
    except Exception as error:
        return templates.TemplateResponse(
            request,
            "manager/dashboard.html",
            {
                "page_title": "Панель менеджера",
                "active_page": "manager",
                "appeals": [],
                "categories": [],
                "statuses": APPEAL_STATUSES,
                "tones": EMOTIONAL_TONES,
                "filters": {"status": status, "category": category, "tone": tone},
                "metrics": {"new": 0, "needs_clarification": 0, "needs_manager": 0},
                "db_error": database_error_message(error),
            },
        )
    finally:
        db.close()


@router.get("/appeals/{appeal_id}", response_class=HTMLResponse)
async def appeal_detail(request: Request, appeal_id: int, error: str = "") -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    try:
        db = open_db()
    except Exception as db_error:
        return templates.TemplateResponse(
            request,
            "manager/appeal_detail.html",
            {
                "page_title": "Обращение",
                "active_page": "manager",
                "appeal": None,
                "statuses": APPEAL_STATUSES,
                "db_error": database_error_message(db_error),
                "error": error,
            },
        )

    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        appeal = db.scalar(
            select(Appeal)
            .where(Appeal.id == appeal_id)
            .options(
                selectinload(Appeal.category),
                selectinload(Appeal.assigned_manager),
                selectinload(Appeal.generated_responses),
                selectinload(Appeal.handover_requests),
                selectinload(Appeal.conversation).selectinload(Conversation.messages),
                selectinload(Appeal.conversation).selectinload(Conversation.client_session).selectinload(ClientSession.user),
            )
        )
        if appeal and current_user.role == "manager" and appeal.assigned_manager_id not in {None, current_user.id}:
            return templates.TemplateResponse(
                request,
                "auth/access_denied.html",
                {"page_title": "Доступ закрыт", "active_page": "manager"},
            )
        return templates.TemplateResponse(
            request,
            "manager/appeal_detail.html",
            {
                "page_title": "Обращение",
                "active_page": "manager",
                "appeal": appeal,
                "statuses": APPEAL_STATUSES,
                "db_error": None,
                "error": error,
            },
        )
    except Exception as error:
        return templates.TemplateResponse(
            request,
            "manager/appeal_detail.html",
            {
                "page_title": "Обращение",
                "active_page": "manager",
                "appeal": None,
                "statuses": APPEAL_STATUSES,
                "db_error": database_error_message(error),
                "error": "",
            },
        )
    finally:
        db.close()


@router.get("/dashboard")
async def manager_dashboard_alias(request: Request, status: str = "", category: str = "", tone: str = ""):
    return await manager_dashboard(request, status=status, category=category, tone=tone)


@router.get("/appeals")
async def manager_appeals_alias(request: Request, status: str = "", category: str = "", tone: str = ""):
    return await manager_dashboard(request, status=status, category=category, tone=tone)


@router.post("/appeals/{appeal_id}/accept")
async def accept_appeal(request: Request, appeal_id: int) -> RedirectResponse:
    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        appeal = db.get(Appeal, appeal_id)
        if appeal:
            appeal.assigned_manager_id = current_user.id
            appeal.status = "assigned_to_manager"
            db.commit()
    finally:
        db.close()
    return redirect_to(f"/manager/appeals/{appeal_id}")


@router.post("/appeals/{appeal_id}/status")
async def update_appeal_status(request: Request, appeal_id: int) -> RedirectResponse:
    form = await read_form(request)
    status = form.get("status", "")
    if status not in APPEAL_STATUSES:
        return redirect_to(f"/manager/appeals/{appeal_id}?error=Некорректный статус")

    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        appeal = db.get(Appeal, appeal_id)
        if appeal and (current_user.role == "admin" or appeal.assigned_manager_id in {None, current_user.id}):
            appeal.status = status
            db.commit()
    finally:
        db.close()
    return redirect_to(f"/manager/appeals/{appeal_id}")


@router.post("/appeals/{appeal_id}/messages")
async def send_manager_message(request: Request, appeal_id: int) -> RedirectResponse:
    form = await read_form(request)
    content = form.get("content", "").strip()
    if not content:
        return redirect_to(f"/manager/appeals/{appeal_id}?error=Введите текст ответа")

    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        appeal = db.scalar(select(Appeal).where(Appeal.id == appeal_id).options(selectinload(Appeal.conversation)))
        if appeal and appeal.conversation and (current_user.role == "admin" or appeal.assigned_manager_id in {None, current_user.id}):
            db.add(Message(conversation_id=appeal.conversation.id, sender_type="manager", content=content))
            if appeal.status not in {"closed"}:
                appeal.status = "manager_answered"
            db.commit()
    finally:
        db.close()
    return redirect_to(f"/manager/appeals/{appeal_id}")
