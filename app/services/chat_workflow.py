from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Appeal,
    ClientSession,
    Conversation,
    GeneratedResponse,
    HandoverRequest,
    Message,
    SentimentAnalysis,
    User,
)
from app.services.classification import classify_request
from app.services.knowledge_base import get_category_by_name, select_knowledge_items
from app.services.response_generation import generate_chat_response
from app.services.sentiment import analyze_sentiment


def create_conversation(db: Session, user: User | None = None) -> Conversation:
    client_session = ClientSession(
        user_id=user.id if user else None,
        client_name=user.full_name if user else None,
        client_contact=user.email if user else None,
        source="website",
        status="active",
    )
    conversation = Conversation(
        client_session=client_session,
        title="Клиентский чат",
        status="open",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(db: Session, conversation_id: int) -> Conversation | None:
    return db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.appeal),
        )
    )


def process_client_message(
    db: Session,
    content: str,
    conversation_id: int | None = None,
    user: User | None = None,
) -> tuple[Conversation, Message, Message, Appeal, list[str], bool]:
    conversation = get_conversation(db, conversation_id) if conversation_id else None
    if conversation is None:
        conversation = create_conversation(db, user)
    elif user and conversation.client_session.user_id != user.id:
        raise PermissionError("Conversation does not belong to current client.")

    classification = classify_request(content)
    sentiment = analyze_sentiment(content)
    category = get_category_by_name(db, classification.category)
    knowledge_items = select_knowledge_items(db, category, sentiment.emotional_tone)
    generated = generate_chat_response(content, classification.category, sentiment.emotional_tone, knowledge_items)

    client_message = Message(
        conversation_id=conversation.id,
        sender_type="client",
        content=content,
    )
    db.add(client_message)
    db.flush()

    db.add(
        SentimentAnalysis(
            message_id=client_message.id,
            emotional_tone=sentiment.emotional_tone,
            confidence=sentiment.confidence,
            explanation=sentiment.explanation,
        )
    )

    appeal = conversation.appeal
    if appeal is None:
        appeal = Appeal(conversation_id=conversation.id)
        db.add(appeal)

    appeal.category_id = category.id if category else None
    appeal.request_category = classification.category
    appeal.emotional_tone = sentiment.emotional_tone
    appeal.status = "needs_manager" if generated.handover_offered else "needs_clarification" if generated.clarifying_questions else "auto_answered"
    appeal.priority = "high" if generated.handover_offered else "normal"

    system_message = Message(
        conversation_id=conversation.id,
        sender_type="system",
        content=generated.text,
    )
    db.add(system_message)
    db.flush()

    db.add(
        GeneratedResponse(
            appeal=appeal,
            response_text=generated.text,
            source=generated.source,
            status=generated.status,
        )
    )

    if generated.handover_offered:
        existing_handover = any(request.status == "new" for request in appeal.handover_requests)
        if not existing_handover:
            db.add(
                HandoverRequest(
                    appeal=appeal,
                    reason="Complex category or emotionally negative request detected by local rules.",
                    status="new",
                )
            )

    db.commit()
    db.refresh(client_message)
    db.refresh(system_message)
    db.refresh(appeal)
    db.refresh(conversation)
    return conversation, client_message, system_message, appeal, generated.clarifying_questions, generated.handover_offered
