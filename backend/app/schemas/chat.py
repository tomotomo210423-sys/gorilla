from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str
    user_id: str
    message: str = Field(min_length=1, max_length=8000)
    character_id: str | None = None
    temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=64, le=8192)
    stream: bool = True


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    model: str
    reasoning_mode: str | None = None
    reasoning_trace: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0


class StreamChunk(BaseModel):
    type: str  # "content" | "done" | "error"
    content: str = ""
    conversation_id: str = ""
