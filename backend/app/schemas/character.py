import uuid
from datetime import datetime
from pydantic import BaseModel


class CharacterCreate(BaseModel):
    name: str
    description: str
    personality: dict | None = None
    speech_style: dict | None = None
    emotion_baseline: dict | None = None
    beliefs: dict | None = None
    background: dict | None = None
    world_setting: str | None = None
    system_prompt_override: str | None = None


class CharacterUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    personality: dict | None = None
    speech_style: dict | None = None
    emotion_baseline: dict | None = None
    beliefs: dict | None = None
    background: dict | None = None
    world_setting: str | None = None
    system_prompt_override: str | None = None


class CharacterOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    personality: dict
    speech_style: dict
    emotion_baseline: dict
    emotion_current: dict
    beliefs: dict
    background: dict
    world_setting: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
