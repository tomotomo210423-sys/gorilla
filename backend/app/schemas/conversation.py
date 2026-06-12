import uuid
from datetime import datetime
from pydantic import BaseModel


class ConversationCreate(BaseModel):
    user_id: str
    character_id: str | None = None
    title: str = "New Conversation"


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    reasoning_trace: str | None = None
    confidence_score: float | None = None

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    summary: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}
