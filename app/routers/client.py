from fastapi import APIRouter, Request
from pathlib import Path

from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import login_redirect, require_role
from app.core.templates import create_templates
from app.db.session import SessionLocal, database_error_message, get_engine
from app.models import AdvertisingReport, Appeal, Conversation, Message

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
        appeals = list(db.scalars(client_appeal_statement(user.id)))
        reports = list(db.scalars(select(AdvertisingReport).where(AdvertisingReport.client_user_id == user.id).order_by(AdvertisingReport.created_at.desc())))
        return templates.TemplateResponse(
            request,
            "client/dashboard.html",
            {"page_title": "Кабинет клиента", "active_page": "client", "appeals": appeals, "reports": reports, "db_error": None},
        )
    finally:
        db.close()


@router.get("/appeals", response_class=HTMLResponse)
async def client_appeals(request: Request) -> HTMLResponse:
    return await client_dashboard(request)


@router.get("/appeals/{appeal_id}", response_class=HTMLResponse)
async def client_appeal_detail(request: Request, appeal_id: int) -> HTMLResponse:
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
                selectinload(Appeal.conversation).selectinload(Conversation.messages),
                selectinload(Appeal.conversation).selectinload(Conversation.messages).selectinload(Message.attachments),
            )
        )
        return templates.TemplateResponse(
            request,
            "client/appeal_detail.html",
            {"page_title": "Мое обращение", "active_page": "client", "appeal": appeal, "db_error": None},
        )
    finally:
        db.close()


@router.get("/chat")
async def client_chat() -> RedirectResponse:
    return redirect_to("/chat/")


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
