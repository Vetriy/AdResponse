from fastapi import APIRouter, Request
from pathlib import Path

from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import login_redirect, require_role
from app.core.templates import create_templates
from app.db.session import SessionLocal, database_error_message, get_engine
from app.models import AdvertisingReport, Appeal, AppealFeedback, Conversation, Message, MessageAttachment
from app.services.feedback import client_ai_feedback_map, client_feedback_for_appeal
from app.services.chat_workflow import generate_auto_reply_for_conversation
from app.services.manager_workflow import get_or_create_report_conversation, get_report_conversation, mark_conversation_read, unread_messages_count
from app.services.uploads import save_upload_file, validate_upload_filename

templates = create_templates()
router = APIRouter(prefix="/client", tags=["client cabinet"])


def redirect_to(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def open_db():
    get_engine()
    return SessionLocal()


def client_appeal_statement(user_id: int):
    return (
        select(Appeal)
        .join(Appeal.conversation)
        .where(Conversation.client_session.has(user_id=user_id))
        .options(selectinload(Appeal.category))
        .order_by(Appeal.created_at.desc())
    )


def build_report_thread_context(reports: list[AdvertisingReport]) -> str | None:
    parts = []
    for report in reports[:5]:
        if report.description:
            parts.append(f"{report.title}: {report.description}")
        else:
            parts.append(report.title)
    return "; ".join(parts) if parts else None


@router.get("/dashboard", response_class=HTMLResponse)
async def client_dashboard(request: Request) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    try:
        db = open_db()
    except Exception as error:
        return templates.TemplateResponse(
            request,
            "client/dashboard.html",
            {"page_title": "Кабинет клиента", "active_page": "client", "appeals": [], "reports": [], "db_error": database_error_message(error)},
        )
    try:
        user = require_role(request, db, {"client"})
        if not hasattr(user, "id"):
            return user
        appeals = list(
            db.scalars(
                client_appeal_statement(user.id).options(
                    selectinload(Appeal.conversation).selectinload(Conversation.messages)
                )
            )
        )
        is_active_client = user.client_type == "active_client"
        reports = []
        report_thread = None
        if is_active_client:
            reports = list(db.scalars(select(AdvertisingReport).where(AdvertisingReport.client_user_id == user.id).order_by(AdvertisingReport.created_at.desc())))
            report_thread = get_report_conversation(db, user.id)
        return templates.TemplateResponse(
            request,
            "client/dashboard.html",
            {
                "page_title": "Кабинет клиента",
                "active_page": "client",
                "appeals": appeals,
                "reports": reports,
                "report_thread": report_thread,
                "is_active_client": is_active_client,
                "db_error": None,
                "unread_messages_count": unread_messages_count,
            },
        )
    finally:
        db.close()


@router.get("/appeals", response_class=HTMLResponse)
async def client_appeals(request: Request) -> HTMLResponse:
    return await client_dashboard(request)


@router.get("/appeals/{appeal_id}", response_class=HTMLResponse)
async def client_appeal_detail(request: Request, appeal_id: int, feedback_error: str = "") -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        user = require_role(request, db, {"client"})
        if not hasattr(user, "id"):
            return user
        appeal = db.scalar(
            select(Appeal)
            .where(Appeal.id == appeal_id)
            .join(Appeal.conversation)
            .where(Conversation.client_session.has(user_id=user.id))
            .options(
                selectinload(Appeal.category),
                selectinload(Appeal.assigned_manager),
                selectinload(Appeal.conversation).selectinload(Conversation.messages),
                selectinload(Appeal.conversation).selectinload(Conversation.messages).selectinload(Message.attachments),
            )
        )
        ai_feedback = {}
        appeal_feedback = None
        if appeal:
            ai_feedback = client_ai_feedback_map(db, user.id, [message.id for message in appeal.conversation.messages if message.sender_type == "system"])
            appeal_feedback = client_feedback_for_appeal(db, appeal.id, user.id)
            mark_conversation_read(appeal.conversation, "client")
            db.commit()
        return templates.TemplateResponse(
            request,
            "client/appeal_detail.html",
            {
                "page_title": "Мое обращение",
                "active_page": "client",
                "appeal": appeal,
                "db_error": None,
                "ai_feedback": ai_feedback,
                "appeal_feedback": appeal_feedback,
                "feedback_error": feedback_error,
            },
        )
    finally:
        db.close()


@router.post("/appeals/{appeal_id}/feedback")
async def submit_appeal_feedback(request: Request, appeal_id: int) -> RedirectResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    form = await request.form()
    try:
        rating = int(str(form.get("rating", "0")))
    except ValueError:
        rating = 0
    comment = str(form.get("comment", "")).strip()
    if rating < 1 or rating > 5:
        return redirect_to(f"/client/appeals/{appeal_id}?feedback_error=Некорректная оценка")

    db = open_db()
    try:
        user = require_role(request, db, {"client"})
        if not hasattr(user, "id"):
            return user
        appeal = db.scalar(
            select(Appeal)
            .where(Appeal.id == appeal_id)
            .join(Appeal.conversation)
            .where(Conversation.client_session.has(user_id=user.id))
        )
        if appeal is None or appeal.status != "closed":
            return redirect_to(f"/client/appeals/{appeal_id}?feedback_error=Оценить можно только завершенное обращение")
        existing = client_feedback_for_appeal(db, appeal.id, user.id)
        if existing is not None:
            return redirect_to(f"/client/appeals/{appeal_id}?feedback_error=Оценка уже сохранена")
        db.add(
            AppealFeedback(
                appeal_id=appeal.id,
                client_user_id=user.id,
                manager_user_id=appeal.assigned_manager_id,
                rating=rating,
                comment=comment or None,
            )
        )
        db.commit()
        return redirect_to(f"/client/appeals/{appeal_id}")
    finally:
        db.close()


@router.get("/chat")
async def client_chat() -> RedirectResponse:
    return redirect_to("/chat/")


@router.get("/reports", response_class=HTMLResponse)
async def client_report_thread(request: Request, error: str = "") -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        user = require_role(request, db, {"client"})
        if not hasattr(user, "id"):
            return user
        if user.client_type != "active_client":
            return templates.TemplateResponse(
                request,
                "auth/access_denied.html",
                {"page_title": "Доступ закрыт", "active_page": "client"},
            )
        conversation = get_or_create_report_conversation(db, user)
        mark_conversation_read(conversation, "client")
        db.commit()
        return templates.TemplateResponse(
            request,
            "client/report_thread.html",
            {
                "page_title": "Отчеты по рекламе",
                "active_page": "client",
                "conversation": get_report_conversation(db, user.id),
                "reports": list(
                    db.scalars(
                        select(AdvertisingReport)
                        .where(AdvertisingReport.client_user_id == user.id)
                        .order_by(AdvertisingReport.created_at.desc())
                    )
                ),
                "error": error,
            },
        )
    finally:
        db.close()


@router.post("/reports/messages")
async def send_client_report_message(request: Request) -> RedirectResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    form = await request.form()
    content = str(form.get("content", "")).strip()
    if not content:
        return redirect_to("/client/reports?error=Введите текст сообщения")
    db = open_db()
    try:
        user = require_role(request, db, {"client"})
        if not hasattr(user, "id"):
            return user
        if user.client_type != "active_client":
            return redirect_to("/client/dashboard")
        conversation = get_or_create_report_conversation(db, user)
        files = [file for file in form.getlist("attachments") if hasattr(file, "filename") and hasattr(file, "read") and file.filename]
        for file in files:
            validate_upload_filename(file.filename)
        message = Message(conversation_id=conversation.id, sender_type="client", content=content)
        db.add(message)
        db.flush()
        for file in files:
            stored = await save_upload_file(file, "messages")
            db.add(
                MessageAttachment(
                    message_id=message.id,
                    uploaded_by_user_id=user.id,
                    original_filename=stored.original_filename,
                    stored_filename=stored.stored_filename,
                    stored_path=stored.stored_path,
                    content_type=stored.content_type,
                    size_bytes=stored.size_bytes,
                )
            )
        reports = list(
            db.scalars(
                select(AdvertisingReport)
                .where(AdvertisingReport.client_user_id == user.id)
                .order_by(AdvertisingReport.created_at.desc())
            )
        )
        system_message = generate_auto_reply_for_conversation(
            db,
            conversation,
            content,
            report_context=build_report_thread_context(reports),
        )
        if system_message:
            db.flush()
        db.commit()
    except ValueError as upload_error:
        db.rollback()
        return redirect_to(f"/client/reports?error={str(upload_error)}")
    finally:
        db.close()
    return redirect_to("/client/reports")


@router.get("/reports/{report_id}")
async def download_report(request: Request, report_id: int):
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        user = require_role(request, db, {"client"})
        if not hasattr(user, "id"):
            return user
        report = db.get(AdvertisingReport, report_id)
        if report is None or report.client_user_id != user.id:
            return templates.TemplateResponse(
                request,
                "auth/access_denied.html",
                {"page_title": "Доступ закрыт", "active_page": "client"},
            )
        path = Path(report.stored_path)
        if not path.exists():
            return templates.TemplateResponse(
                request,
                "client/dashboard.html",
                {"page_title": "Кабинет клиента", "active_page": "client", "appeals": [], "reports": [], "db_error": "Файл отчета не найден."},
            )
        return FileResponse(path, media_type=report.content_type, filename=report.original_filename)
    finally:
        db.close()
