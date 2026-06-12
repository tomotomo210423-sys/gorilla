import uuid
from datetime import datetime
from pydantic import BaseModel


class MemoryEntryOut(BaseModel):
    id: uuid.UUID
    memory_type: str
    content: str
    importance_score: float
    retention_score: float
    access_count: int
    tags: list[str]
    topic: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
