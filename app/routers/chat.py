from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import login_redirect, require_role
from app.core.templates import create_templates
from app.db.session import SessionLocal, database_error_message, get_engine
from app.models import AdvertisingReport, Appeal, Conversation, Message, MessageAttachment
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatSendResponse,
    ConversationCreateResponse,
    ConversationHistoryResponse,
)
from app.services.chat_workflow import create_conversation, get_conversation, process_client_message
from app.services.labels import category_label, status_label, tone_label
from app.services.feedback import client_ai_feedback_map, store_or_update_ai_feedback
from app.services.uploads import is_image_upload, save_upload_file, validate_upload_filename

templates = create_templates()
router = APIRouter(prefix="/chat", tags=["client chat"])


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request, report_id: int | None = None) -> HTMLResponse:
    report = None
    try:
        get_engine()
        db = SessionLocal()
    except Exception:
        if not request.session.get("user"):
            return login_redirect(request)
        db = None
    if db:
        try:
            user = require_role(request, db, {"client"})
            if not hasattr(user, "id"):
                return user
            if report_id:
                report = db.get(AdvertisingReport, report_id)
                if report is None or report.client_user_id != user.id:
                    report = None
        finally:
            db.close()
    return templates.TemplateResponse(
        request,
        "chat/index.html",
        {
            "page_title": "Клиентский чат",
            "active_page": "chat",
            "report": report,
        },
    )


def serialize_attachment(attachment: MessageAttachment):
    return {
        "id": attachment.id,
        "original_filename": attachment.original_filename,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "url": f"/chat/attachments/{attachment.id}",
        "is_image": is_image_upload(attachment.original_filename),
    }


def serialize_message(message: Message, feedback_map: dict[int, object] | None = None) -> ChatMessageRead:
    feedback = feedback_map.get(message.id) if feedback_map else None
    return ChatMessageRead(
        id=message.id,
        sender_type=message.sender_type,
        sender_display_name=message.sender_display_name,
        content=message.content,
        created_at=message.created_at,
        attachments=[serialize_attachment(attachment) for attachment in message.attachments],
        ai_feedback_value=feedback.value if feedback else None,
        ai_feedback_reason=feedback.reason if feedback else None,
        ai_feedback_custom_reason=feedback.custom_reason if feedback else None,
    )


def get_chat_db():
    try:
        get_engine()
        db = SessionLocal()
    except Exception as error:
        raise HTTPException(status_code=503, detail=database_error_message(error)) from error

    try:
        yield db
    finally:
        db.close()


def get_report_context(db: Session, report_id: int | None, user_id: int) -> str | None:
    if not report_id:
        return None
    report = db.get(AdvertisingReport, report_id)
    if report is None or report.client_user_id != user_id:
        raise HTTPException(status_code=403, detail="Report access denied.")
    if report.description:
        return f"{report.title}. {report.description}"
    return report.title


async def save_message_attachments(db: Session, message: Message, files: list[UploadFile], user_id: int) -> None:
    for file in files:
        if not file.filename:
            continue
        stored = await save_upload_file(file, "messages")
        db.add(
            MessageAttachment(
                message_id=message.id,
                uploaded_by_user_id=user_id,
                original_filename=stored.original_filename,
                stored_filename=stored.stored_filename,
                stored_path=stored.stored_path,
                content_type=stored.content_type,
                size_bytes=stored.size_bytes,
            )
        )
    db.commit()


@router.post("/api/conversations", response_model=ConversationCreateResponse)
def create_chat_conversation(request: Request, db: Session = Depends(get_chat_db)) -> ConversationCreateResponse:
    user = require_role(request, db, {"client"})
    if not hasattr(user, "id"):
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        conversation = create_conversation(db, user)
    except Exception as error:
        raise HTTPException(status_code=503, detail=database_error_message(error)) from error

    return ConversationCreateResponse(conversation_id=conversation.id)


@router.get("/api/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
def read_chat_history(request: Request, conversation_id: int, db: Session = Depends(get_chat_db)) -> ConversationHistoryResponse:
    user = require_role(request, db, {"client"})
    if not hasattr(user, "id"):
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        conversation = get_conversation(db, conversation_id)
    except Exception as error:
        raise HTTPException(status_code=503, detail=database_error_message(error)) from error

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation was not found.")
    if conversation.client_session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    appeal = conversation.appeal
    feedback_map = client_ai_feedback_map(db, user.id, [message.id for message in conversation.messages if message.sender_type == "system"])
    return ConversationHistoryResponse(
        conversation_id=conversation.id,
        messages=[serialize_message(message, feedback_map) for message in conversation.messages],
        category=appeal.request_category if appeal else None,
        category_label=category_label(appeal.request_category) if appeal else None,
        emotional_tone=appeal.emotional_tone if appeal else None,
        emotional_tone_label=tone_label(appeal.emotional_tone) if appeal else None,
        status=appeal.status if appeal else conversation.status,
        status_label=status_label(appeal.status if appeal else conversation.status),
    )


@router.post("/api/messages", response_model=ChatSendResponse)
def send_chat_message(request: Request, payload: ChatMessageCreate, db: Session = Depends(get_chat_db)) -> ChatSendResponse:
    user = require_role(request, db, {"client"})
    if not hasattr(user, "id"):
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        report_context = get_report_context(db, payload.report_id, user.id)
        conversation, client_message, system_message, appeal, questions, handover_offered = process_client_message(
            db,
            payload.content.strip(),
            payload.conversation_id,
            user,
            report_context=report_context,
        )
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail=database_error_message(error)) from error
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=503, detail=database_error_message(error)) from error

    return ChatSendResponse(
        conversation_id=conversation.id,
        client_message=serialize_message(client_message),
        system_message=serialize_message(system_message) if system_message else None,
        category=appeal.request_category or "other",
        category_label=category_label(appeal.request_category),
        emotional_tone=appeal.emotional_tone or "neutral",
        emotional_tone_label=tone_label(appeal.emotional_tone),
        status_label=status_label(appeal.status),
        handover_offered=handover_offered,
        clarifying_questions=questions,
    )


@router.post("/api/messages/upload", response_model=ChatSendResponse)
async def send_chat_message_with_uploads(request: Request, db: Session = Depends(get_chat_db)) -> ChatSendResponse:
    user = require_role(request, db, {"client"})
    if not hasattr(user, "id"):
        raise HTTPException(status_code=401, detail="Authentication required.")

    try:
        form = await request.form()
        content = str(form.get("content", "")).strip()
        if not content:
            raise HTTPException(status_code=422, detail="Введите текст сообщения.")
        conversation_id_value = str(form.get("conversation_id", "")).strip()
        report_id_value = str(form.get("report_id", "")).strip()
        conversation_id = int(conversation_id_value) if conversation_id_value.isdigit() else None
        report_id = int(report_id_value) if report_id_value.isdigit() else None
        files = [file for file in form.getlist("attachments") if hasattr(file, "filename") and hasattr(file, "read")]
        for file in files:
            if file.filename:
                validate_upload_filename(file.filename)

        report_context = get_report_context(db, report_id, user.id)
        conversation, client_message, system_message, appeal, questions, handover_offered = process_client_message(
            db,
            content,
            conversation_id,
            user,
            report_context=report_context,
        )
        await save_message_attachments(db, client_message, files, user.id)
        db.refresh(client_message)
        if system_message:
            db.refresh(system_message)
    except HTTPException:
        raise
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail=database_error_message(error)) from error
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=503, detail=database_error_message(error)) from error

    return ChatSendResponse(
        conversation_id=conversation.id,
        client_message=serialize_message(client_message),
        system_message=serialize_message(system_message) if system_message else None,
        category=appeal.request_category or "other",
        category_label=category_label(appeal.request_category),
        emotional_tone=appeal.emotional_tone or "neutral",
        emotional_tone_label=tone_label(appeal.emotional_tone),
        status_label=status_label(appeal.status),
        handover_offered=handover_offered,
        clarifying_questions=questions,
    )


@router.get("/attachments/{attachment_id}")
def download_message_attachment(request: Request, attachment_id: int, db: Session = Depends(get_chat_db)) -> FileResponse:
    current_user = require_role(request, db, {"client", "manager", "admin"})
    if not hasattr(current_user, "id"):
        raise HTTPException(status_code=401, detail="Authentication required.")
    attachment = db.scalar(
        select(MessageAttachment)
        .where(MessageAttachment.id == attachment_id)
        .options(
            selectinload(MessageAttachment.message)
            .selectinload(Message.conversation)
            .selectinload(Conversation.client_session)
        )
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment was not found.")
    if current_user.role == "client" and attachment.message.conversation.client_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    path = Path(attachment.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File was not found.")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_filename)


@router.post("/api/messages/{message_id}/feedback")
async def rate_ai_message(request: Request, message_id: int, db: Session = Depends(get_chat_db)) -> dict[str, str]:
    user = require_role(request, db, {"client"})
    if not hasattr(user, "id"):
        raise HTTPException(status_code=401, detail="Authentication required.")
    form = await request.form()
    message = db.scalar(
        select(Message)
        .where(Message.id == message_id, Message.sender_type == "system")
        .options(selectinload(Message.conversation).selectinload(Conversation.client_session))
    )
    if message is None or message.conversation.client_session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ответ не найден.")
    appeal = db.scalar(select(Appeal).where(Appeal.conversation_id == message.conversation_id))
    if appeal is None:
        raise HTTPException(status_code=404, detail="Обращение не найдено.")
    try:
        feedback = store_or_update_ai_feedback(
            db,
            message_id=message.id,
            appeal_id=appeal.id,
            client_user_id=user.id,
            value=str(form.get("value", "")),
            reason=str(form.get("reason", "")),
            custom_reason=str(form.get("custom_reason", "")),
        )
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"status": "ok", "value": feedback.value, "reason": feedback.reason or ""}
