from datetime import datetime

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
from app.services.knowledge_base import resolve_active_category, select_knowledge_items
from app.services.response_generation import build_dialogue_context, generate_chat_response
from app.services.sentiment import analyze_sentiment


def report_context_for_linked_appeal(appeal: Appeal | None) -> str | None:
    if appeal is None or not appeal.advertising_reports:
        return None
    parts = []
    for report in sorted(appeal.advertising_reports, key=lambda item: (item.created_at or datetime.min, item.id or 0), reverse=True)[:3]:
        parts.append(f"{report.title}: {report.description}" if report.description else report.title)
    return "; ".join(parts) if parts else None


def analysis_text_for_dialogue(content: str, conversation: Conversation) -> str:
    context = build_dialogue_context(content, conversation.messages)
    if not context.previous_client_messages and not context.previous_system_messages and not context.previous_manager_messages:
        return content
    return f"Последнее сообщение клиента: {content}\nПредыдущий контекст:\n{context.all_text}"


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
        conversation_type="appeal",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def generate_auto_reply_for_conversation(
    db: Session,
    conversation: Conversation,
    content: str,
    report_context: str | None = None,
) -> Message | None:
    if not conversation.auto_reply_enabled:
        conversation.status = "needs_manager"
        return None

    dialogue_context = build_dialogue_context(content, conversation.messages, report_context=report_context)
    analysis_text = analysis_text_for_dialogue(content, conversation)
    classification = classify_request(analysis_text)
    sentiment = analyze_sentiment(analysis_text)
    category, effective_category = resolve_active_category(db, classification.category)
    knowledge_items = select_knowledge_items(db, category, sentiment.emotional_tone)
    generated = generate_chat_response(
        content,
        effective_category,
        sentiment.emotional_tone,
        knowledge_items,
        report_context=report_context,
        dialogue_context=dialogue_context,
    )
    system_message = Message(
        conversation_id=conversation.id,
        sender_type="system",
        content=generated.text,
    )
    db.add(system_message)
    conversation.status = "needs_manager" if generated.handover_offered else "auto_answered"
    return system_message


def get_conversation(db: Session, conversation_id: int) -> Conversation | None:
    return db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.messages).selectinload(Message.attachments),
            selectinload(Conversation.appeal).selectinload(Appeal.advertising_reports),
        )
    )


def process_client_message(
    db: Session,
    content: str,
    conversation_id: int | None = None,
    user: User | None = None,
    report_context: str | None = None,
) -> tuple[Conversation, Message, Message | None, Appeal, list[str], bool]:
    conversation = get_conversation(db, conversation_id) if conversation_id else None
    if conversation is None:
        conversation = create_conversation(db, user)
    elif user and conversation.client_session.user_id != user.id:
        raise PermissionError("Conversation does not belong to current client.")

    client_message = Message(
        conversation_id=conversation.id,
        sender_type="client",
        sender_display_name=user.full_name or user.username if user else None,
        content=content,
    )
    db.add(client_message)
    db.flush()

    appeal = conversation.appeal
    if appeal is None:
        appeal = Appeal(conversation_id=conversation.id, auto_reply_enabled=True)
        db.add(appeal)

    effective_report_context = report_context
    if effective_report_context is None and conversation.conversation_type == "appeal":
        effective_report_context = report_context_for_linked_appeal(appeal)

    dialogue_context = build_dialogue_context(content, conversation.messages, report_context=effective_report_context)
    analysis_text = analysis_text_for_dialogue(content, conversation)
    classification = classify_request(analysis_text)
    sentiment = analyze_sentiment(analysis_text)
    category, effective_category = resolve_active_category(db, classification.category)

    db.add(
        SentimentAnalysis(
            message_id=client_message.id,
            emotional_tone=sentiment.emotional_tone,
            confidence=sentiment.confidence,
            explanation=sentiment.explanation,
        )
    )

    appeal.category_id = category.id if category else None
    appeal.request_category = effective_category
    appeal.emotional_tone = sentiment.emotional_tone
    if not appeal.auto_reply_enabled:
        appeal.status = "needs_manager"
        appeal.priority = "high"
        db.commit()
        db.refresh(client_message)
        db.refresh(appeal)
        db.refresh(conversation)
        return conversation, client_message, None, appeal, [], True

    knowledge_items = select_knowledge_items(db, category, sentiment.emotional_tone)
    generated = generate_chat_response(
        content,
        effective_category,
        sentiment.emotional_tone,
        knowledge_items,
        report_context=effective_report_context,
        dialogue_context=dialogue_context,
    )
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
