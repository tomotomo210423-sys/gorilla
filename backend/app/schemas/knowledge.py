from pydantic import BaseModel, Field


class DocumentIngestRequest(BaseModel):
    user_id: str
    content: str = Field(min_length=10)
    source: str = ""
    metadata: dict | None = None
