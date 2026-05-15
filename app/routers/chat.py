from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/chat", tags=["client chat"])


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request) -> HTMLResponse:
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
def create_chat_conversation(db: Session = Depends(get_chat_db)) -> ConversationCreateResponse:
    try:
        conversation = create_conversation(db)
    except Exception as error:
        raise HTTPException(status_code=503, detail=database_error_message(error)) from error

    return ConversationCreateResponse(conversation_id=conversation.id)


@router.get("/api/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
def read_chat_history(conversation_id: int, db: Session = Depends(get_chat_db)) -> ConversationHistoryResponse:
    try:
        conversation = get_conversation(db, conversation_id)
    except Exception as error:
        raise HTTPException(status_code=503, detail=database_error_message(error)) from error

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation was not found.")

    appeal = conversation.appeal
    return ConversationHistoryResponse(
        conversation_id=conversation.id,
        messages=[serialize_message(message) for message in conversation.messages],
        category=appeal.request_category if appeal else None,
        emotional_tone=appeal.emotional_tone if appeal else None,
        status=appeal.status if appeal else conversation.status,
    )


@router.post("/api/messages", response_model=ChatSendResponse)
def send_chat_message(payload: ChatMessageCreate, db: Session = Depends(get_chat_db)) -> ChatSendResponse:
    try:
        conversation, client_message, system_message, appeal, questions, handover_offered = process_client_message(
            db,
            payload.content.strip(),
            payload.conversation_id,
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
