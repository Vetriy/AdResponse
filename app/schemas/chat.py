from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreateResponse(BaseModel):
    conversation_id: int


class ChatMessageCreate(BaseModel):
    conversation_id: int | None = None
    content: str = Field(min_length=1, max_length=4000)


class ChatMessageRead(BaseModel):
    id: int
    sender_type: str
    content: str
    created_at: datetime


class ChatSendResponse(BaseModel):
    conversation_id: int
    client_message: ChatMessageRead
    system_message: ChatMessageRead
    category: str
    emotional_tone: str
    handover_offered: bool
    clarifying_questions: list[str]


class ConversationHistoryResponse(BaseModel):
    conversation_id: int
    messages: list[ChatMessageRead]
    category: str | None = None
    emotional_tone: str | None = None
    status: str | None = None
