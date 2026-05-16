from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import login_redirect, require_role
from app.core.templates import create_templates
from app.db.session import SessionLocal, database_error_message, get_engine
from app.models import AdvertisingReport, Appeal, Category, ClientSession, Conversation, Message, MessageAttachment, User
from app.services.feedback import manager_rating_summary
from app.services.manager_workflow import (
    finish_appeal_for_manager,
    get_or_create_report_conversation,
    get_report_conversation,
    group_manager_appeals,
    list_manager_clients,
    mark_conversation_read,
    resolve_appeal_client_user,
    unread_messages_count,
)
from app.services.uploads import save_upload_file, validate_upload_filename

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
CLIENT_TYPES = ("active_client", "potential_client")


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
    client_id: int | None = None,
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
                "filters": {"status": status, "category": category, "tone": tone, "client_id": client_id},
                "metrics": {"new": 0, "needs_clarification": 0, "needs_manager": 0},
                "appeal_groups": {"unassigned": [], "mine": [], "other": [], "completed": []},
                "client_filter": None,
                "rating_summary": None,
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
            "needs_manager": sum(1 for appeal in all_appeals if appeal.status in {"needs_manager", "handover_requested"}),
        }

        statement = (
            select(Appeal)
            .options(
                selectinload(Appeal.category),
                selectinload(Appeal.assigned_manager),
                selectinload(Appeal.conversation).selectinload(Conversation.messages),
                selectinload(Appeal.conversation).selectinload(Conversation.client_session).selectinload(ClientSession.user),
            )
        )
        if status:
            statement = statement.where(Appeal.status == status)
        if category and category.isdigit():
            statement = statement.where(Appeal.category_id == int(category))
        if tone:
            statement = statement.where(Appeal.emotional_tone == tone)
        client_filter = None
        if client_id:
            client_filter = db.get(User, client_id)
            if client_filter and client_filter.role == "client":
                statement = statement.join(Appeal.conversation).join(Conversation.client_session).where(ClientSession.user_id == client_filter.id)
            else:
                client_filter = None

        appeals = list(db.scalars(statement))
        appeal_groups = group_manager_appeals(appeals, current_user.id if current_user.role == "manager" else None)
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
                "filters": {"status": status, "category": category, "tone": tone, "client_id": client_id},
                "metrics": metrics,
                "appeal_groups": appeal_groups,
                "client_filter": client_filter,
                "rating_summary": manager_rating_summary(db, current_user.id if current_user.role == "manager" else None),
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
                "filters": {"status": status, "category": category, "tone": tone, "client_id": client_id},
                "metrics": {"new": 0, "needs_clarification": 0, "needs_manager": 0},
                "appeal_groups": {"unassigned": [], "mine": [], "other": [], "completed": []},
                "client_filter": None,
                "rating_summary": None,
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
                "rating_summary": None,
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
                selectinload(Appeal.advertising_reports),
                selectinload(Appeal.conversation).selectinload(Conversation.messages),
                selectinload(Appeal.conversation).selectinload(Conversation.messages).selectinload(Message.attachments),
                selectinload(Appeal.conversation).selectinload(Conversation.client_session).selectinload(ClientSession.user),
            )
        )
        if appeal and current_user.role == "manager" and appeal.assigned_manager_id not in {None, current_user.id}:
            return templates.TemplateResponse(
                request,
                "auth/access_denied.html",
                {"page_title": "Доступ закрыт", "active_page": "manager"},
            )
        if appeal:
            mark_conversation_read(appeal.conversation, current_user.role)
            db.commit()
        return templates.TemplateResponse(
            request,
            "manager/appeal_detail.html",
            {
                "page_title": "Обращение",
                "active_page": "manager",
                "appeal": appeal,
                "statuses": APPEAL_STATUSES,
                "rating_summary": manager_rating_summary(db, appeal.assigned_manager_id) if appeal and appeal.assigned_manager_id else None,
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
                "rating_summary": None,
                "db_error": database_error_message(error),
                "error": "",
            },
        )
    finally:
        db.close()


@router.get("/dashboard")
async def manager_dashboard_alias(request: Request, status: str = "", category: str = "", tone: str = "", client_id: int | None = None):
    return await manager_dashboard(request, status=status, category=category, tone=tone, client_id=client_id)


@router.get("/appeals")
async def manager_appeals_alias(request: Request, status: str = "", category: str = "", tone: str = "", client_id: int | None = None):
    return await manager_dashboard(request, status=status, category=category, tone=tone, client_id=client_id)


@router.get("/clients", response_class=HTMLResponse)
async def manager_clients(request: Request) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        return templates.TemplateResponse(
            request,
            "manager/clients.html",
            {
                "page_title": "Клиенты",
                "active_page": "manager-clients",
                "clients": list_manager_clients(db),
                "client_types": CLIENT_TYPES,
                "db_error": None,
            },
        )
    except Exception as error:
        return templates.TemplateResponse(
            request,
            "manager/clients.html",
            {
                "page_title": "Клиенты",
                "active_page": "manager-clients",
                "clients": [],
                "client_types": CLIENT_TYPES,
                "db_error": database_error_message(error),
            },
        )
    finally:
        db.close()


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
            appeal.auto_reply_enabled = False
            db.commit()
    finally:
        db.close()
    return redirect_to(f"/manager/appeals/{appeal_id}")


@router.post("/clients/{client_id}/type")
async def update_client_type(request: Request, client_id: int) -> RedirectResponse:
    form = await read_form(request)
    client_type = form.get("client_type", "")
    if client_type not in CLIENT_TYPES:
        return redirect_to("/manager/clients")
    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        client = db.get(User, client_id)
        if client and client.role == "client":
            client.client_type = client_type
            db.commit()
    finally:
        db.close()
    return redirect_to("/manager/clients")


@router.post("/appeals/{appeal_id}/auto-reply")
async def toggle_auto_reply(request: Request, appeal_id: int) -> RedirectResponse:
    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        appeal = db.get(Appeal, appeal_id)
        if appeal and (current_user.role == "admin" or appeal.assigned_manager_id in {None, current_user.id}):
            appeal.auto_reply_enabled = not appeal.auto_reply_enabled
            if not appeal.auto_reply_enabled and appeal.status != "closed":
                appeal.status = "needs_manager"
            db.commit()
    finally:
        db.close()
    return redirect_to(f"/manager/appeals/{appeal_id}")


@router.post("/appeals/{appeal_id}/finish")
async def finish_appeal(request: Request, appeal_id: int) -> RedirectResponse:
    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        appeal = db.get(Appeal, appeal_id)
        if finish_appeal_for_manager(appeal, current_user):
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
    form = await request.form()
    content = str(form.get("content", "")).strip()
    if not content:
        return redirect_to(f"/manager/appeals/{appeal_id}?error=Введите текст ответа")

    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        appeal = db.scalar(select(Appeal).where(Appeal.id == appeal_id).options(selectinload(Appeal.conversation)))
        if appeal and appeal.conversation and (current_user.role == "admin" or appeal.assigned_manager_id in {None, current_user.id}):
            files = [file for file in form.getlist("attachments") if hasattr(file, "filename") and hasattr(file, "read") and file.filename]
            for file in files:
                validate_upload_filename(file.filename)
            message = Message(conversation_id=appeal.conversation.id, sender_type="manager", content=content)
            db.add(message)
            db.flush()
            for file in files:
                stored = await save_upload_file(file, "messages")
                db.add(
                    MessageAttachment(
                        message_id=message.id,
                        uploaded_by_user_id=current_user.id,
                        original_filename=stored.original_filename,
                        stored_filename=stored.stored_filename,
                        stored_path=stored.stored_path,
                        content_type=stored.content_type,
                        size_bytes=stored.size_bytes,
                    )
                )
            if appeal.status not in {"closed"}:
                appeal.status = "manager_answered"
            db.commit()
    except ValueError as error:
        db.rollback()
        return redirect_to(f"/manager/appeals/{appeal_id}?error={str(error)}")
    finally:
        db.close()
    return redirect_to(f"/manager/appeals/{appeal_id}")


@router.post("/appeals/{appeal_id}/reports")
async def upload_appeal_report(request: Request, appeal_id: int) -> RedirectResponse:
    form = await request.form()
    title = str(form.get("title", "")).strip()
    description = str(form.get("description", "")).strip()
    file = form.get("report_file")
    if not title or not hasattr(file, "filename") or not hasattr(file, "read") or not file.filename:
        return redirect_to(f"/manager/appeals/{appeal_id}?error=Укажите название отчета и файл")

    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        appeal = db.scalar(
            select(Appeal)
            .where(Appeal.id == appeal_id)
            .options(
                selectinload(Appeal.conversation)
                .selectinload(Conversation.client_session)
                .selectinload(ClientSession.user)
            )
        )
        client = resolve_appeal_client_user(db, appeal)
        if appeal is None or client is None:
            return redirect_to(f"/manager/appeals/{appeal_id}?error=Клиент обращения не найден")
        if client.client_type != "active_client":
            return redirect_to(f"/manager/appeals/{appeal_id}?error=Отчеты доступны только для действующих клиентов")
        if current_user.role == "manager" and appeal.assigned_manager_id not in {None, current_user.id}:
            return redirect_to(f"/manager/appeals/{appeal_id}?error=Обращение закреплено за другим менеджером")
        validate_upload_filename(file.filename)
        stored = await save_upload_file(file, "reports")
        report_conversation = get_or_create_report_conversation(db, client)
        message = Message(
            conversation_id=report_conversation.id,
            sender_type="manager",
            content=f"Загружен рекламный отчет: {title}" + (f"\n{description}" if description else ""),
        )
        db.add(message)
        db.add(
            AdvertisingReport(
                client_user_id=client.id,
                appeal_id=appeal.id,
                conversation_id=report_conversation.id,
                uploaded_by_user_id=current_user.id,
                title=title,
                description=description or None,
                original_filename=stored.original_filename,
                stored_filename=stored.stored_filename,
                stored_path=stored.stored_path,
                content_type=stored.content_type,
                size_bytes=stored.size_bytes,
            )
        )
        db.commit()
    except ValueError as error:
        db.rollback()
        return redirect_to(f"/manager/appeals/{appeal_id}?error={str(error)}")
    finally:
        db.close()
    return redirect_to(f"/manager/appeals/{appeal_id}")


@router.get("/clients/{client_id}/reports", response_class=HTMLResponse)
async def manager_report_thread(request: Request, client_id: int, error: str = "") -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        client = db.get(User, client_id)
        if client is None or client.role != "client" or client.client_type != "active_client":
            return templates.TemplateResponse(
                request,
                "auth/access_denied.html",
                {"page_title": "Доступ закрыт", "active_page": "manager-clients"},
            )
        conversation = get_or_create_report_conversation(db, client)
        mark_conversation_read(conversation, current_user.role)
        db.commit()
        db.refresh(conversation)
        return templates.TemplateResponse(
            request,
            "manager/report_thread.html",
            {
                "page_title": "Отчеты клиента",
                "active_page": "manager-clients",
                "client": client,
                "conversation": get_report_conversation(db, client.id),
                "reports": list(
                    db.scalars(
                        select(AdvertisingReport)
                        .where(AdvertisingReport.client_user_id == client.id)
                        .order_by(AdvertisingReport.created_at.desc())
                    )
                ),
                "unread_count": unread_messages_count(conversation, current_user.role),
                "error": error,
            },
        )
    finally:
        db.close()


@router.post("/clients/{client_id}/reports/messages")
async def send_manager_report_message(request: Request, client_id: int) -> RedirectResponse:
    form = await request.form()
    content = str(form.get("content", "")).strip()
    if not content:
        return redirect_to(f"/manager/clients/{client_id}/reports?error=Введите текст сообщения")
    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        client = db.get(User, client_id)
        if client is None or client.role != "client" or client.client_type != "active_client":
            return redirect_to("/manager/clients")
        conversation = get_or_create_report_conversation(db, client)
        files = [file for file in form.getlist("attachments") if hasattr(file, "filename") and hasattr(file, "read") and file.filename]
        for file in files:
            validate_upload_filename(file.filename)
        message = Message(conversation_id=conversation.id, sender_type="manager", content=content)
        db.add(message)
        db.flush()
        for file in files:
            stored = await save_upload_file(file, "messages")
            db.add(
                MessageAttachment(
                    message_id=message.id,
                    uploaded_by_user_id=current_user.id,
                    original_filename=stored.original_filename,
                    stored_filename=stored.stored_filename,
                    stored_path=stored.stored_path,
                    content_type=stored.content_type,
                    size_bytes=stored.size_bytes,
                )
            )
        db.commit()
    except ValueError as error:
        db.rollback()
        return redirect_to(f"/manager/clients/{client_id}/reports?error={str(error)}")
    finally:
        db.close()
    return redirect_to(f"/manager/clients/{client_id}/reports")


@router.post("/clients/{client_id}/reports/upload")
async def upload_client_report(request: Request, client_id: int) -> RedirectResponse:
    form = await request.form()
    title = str(form.get("title", "")).strip()
    description = str(form.get("description", "")).strip()
    file = form.get("report_file")
    if not title or not hasattr(file, "filename") or not hasattr(file, "read") or not file.filename:
        return redirect_to(f"/manager/clients/{client_id}/reports?error=Укажите название отчета и файл")
    db = open_db()
    try:
        current_user = require_role(request, db, {"manager", "admin"})
        if not hasattr(current_user, "id"):
            return current_user
        client = db.get(User, client_id)
        if client is None or client.role != "client" or client.client_type != "active_client":
            return redirect_to("/manager/clients")
        validate_upload_filename(file.filename)
        stored = await save_upload_file(file, "reports")
        conversation = get_or_create_report_conversation(db, client)
        db.add(
            Message(
                conversation_id=conversation.id,
                sender_type="manager",
                content=f"Загружен рекламный отчет: {title}" + (f"\n{description}" if description else ""),
            )
        )
        db.add(
            AdvertisingReport(
                client_user_id=client.id,
                conversation_id=conversation.id,
                uploaded_by_user_id=current_user.id,
                title=title,
                description=description or None,
                original_filename=stored.original_filename,
                stored_filename=stored.stored_filename,
                stored_path=stored.stored_path,
                content_type=stored.content_type,
                size_bytes=stored.size_bytes,
            )
        )
        db.commit()
    except ValueError as error:
        db.rollback()
        return redirect_to(f"/manager/clients/{client_id}/reports?error={str(error)}")
    finally:
        db.close()
    return redirect_to(f"/manager/clients/{client_id}/reports")
