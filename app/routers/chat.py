from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import login_redirect, require_role
from app.core.templates import create_templates
from app.db.session import SessionLocal, database_error_message, get_engine
from app.models import Message
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatSendResponse,
    ConversationCreateResponse,
    ConversationHistoryResponse,
)
from app.services.chat_workflow import create_conversation, get_conversation, process_client_message

templates = create_templates()
router = APIRouter(prefix="/chat", tags=["client chat"])


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request) -> HTMLResponse:
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
        finally:
            db.close()
    return templates.TemplateResponse(
        request,
        "chat/index.html",
        {
            "page_title": "Клиентский чат",
            "active_page": "chat",
        },
    )


def serialize_message(message: Message) -> ChatMessageRead:
    return ChatMessageRead(
        id=message.id,
        sender_type=message.sender_type,
        content=message.content,
        created_at=message.created_at,
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
    return ConversationHistoryResponse(
        conversation_id=conversation.id,
        messages=[serialize_message(message) for message in conversation.messages],
        category=appeal.request_category if appeal else None,
        emotional_tone=appeal.emotional_tone if appeal else None,
        status=appeal.status if appeal else conversation.status,
    )


@router.post("/api/messages", response_model=ChatSendResponse)
def send_chat_message(request: Request, payload: ChatMessageCreate, db: Session = Depends(get_chat_db)) -> ChatSendResponse:
    user = require_role(request, db, {"client"})
    if not hasattr(user, "id"):
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        conversation, client_message, system_message, appeal, questions, handover_offered = process_client_message(
            db,
            payload.content.strip(),
            payload.conversation_id,
            user,
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
        system_message=serialize_message(system_message),
        category=appeal.request_category or "other",
        emotional_tone=appeal.emotional_tone or "neutral",
        handover_offered=handover_offered,
        clarifying_questions=questions,
    )
