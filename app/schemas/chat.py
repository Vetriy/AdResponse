from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreateResponse(BaseModel):
    conversation_id: int


class ChatMessageCreate(BaseModel):
    conversation_id: int | None = None
    report_id: int | None = None
    content: str = Field(min_length=1, max_length=4000)


class AttachmentRead(BaseModel):
    id: int
    original_filename: str
    content_type: str | None = None
    size_bytes: int
    url: str
    is_image: bool


class ChatMessageRead(BaseModel):
    id: int
    sender_type: str
    content: str
    created_at: datetime
    attachments: list[AttachmentRead] = Field(default_factory=list)
    ai_feedback_value: str | None = None
    ai_feedback_reason: str | None = None
    ai_feedback_custom_reason: str | None = None


class ChatSendResponse(BaseModel):
    conversation_id: int
    client_message: ChatMessageRead
    system_message: ChatMessageRead
    category: str
    category_label: str
    emotional_tone: str
    emotional_tone_label: str
    status_label: str | None = None
    handover_offered: bool
    clarifying_questions: list[str]


class ConversationHistoryResponse(BaseModel):
    conversation_id: int
    messages: list[ChatMessageRead]
    category: str | None = None
    category_label: str | None = None
    emotional_tone: str | None = None
    emotional_tone_label: str | None = None
    status: str | None = None
    status_label: str | None = None
