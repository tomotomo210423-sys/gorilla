"""
Episodic Memory: Time-ordered events and experiences.
Captures WHO, WHAT, WHEN, WHERE, HOW of significant events.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.memory import MemoryEntry, MemoryType
from app.core.llm.base import BaseLLMClient, LLMMessage, GenerationConfig

logger = structlog.get_logger()

EPISODE_EXTRACTION_PROMPT = """以下の会話から重要なエピソード（出来事）を抽出してください。

会話:
{conversation}

以下のJSON形式で出力してください（重要なエピソードがなければ空リストを返す）:
[
  {{
    "event": "何が起きたか",
    "participants": ["関係者"],
    "emotion": "感情的な意味合い",
    "importance": 0.0から1.0,
    "tags": ["タグ"]
  }}
]"""


@dataclass
class Episode:
    event: str
    participants: list[str]
    emotion: str
    importance: float
    tags: list[str]
    timestamp: datetime


class EpisodicMemory:
    def __init__(self, db: AsyncSession, llm: BaseLLMClient):
        self.db = db
        self.llm = llm

    async def extract_and_store(
        self,
        user_id: UUID,
        conversation_id: UUID,
        messages: list[dict],
        character_id: UUID | None = None,
    ) -> list[MemoryEntry]:
        if not messages:
            return []

        conversation_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in messages
        )

        try:
            result = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="user",
                        content=EPISODE_EXTRACTION_PROMPT.format(
                            conversation=conversation_text
                        ),
                    )
                ],
                config=GenerationConfig(temperature=0.2, max_tokens=512),
            )
            import json

            episodes_data = json.loads(result.content)
            if not isinstance(episodes_data, list):
                return []
        except Exception as e:
            logger.warning("episode_extraction_failed", error=str(e))
            return []

        entries = []
        for ep_data in episodes_data:
            importance = float(ep_data.get("importance", 0.5))
            if importance < 0.3:
                continue

            entry = MemoryEntry(
                user_id=user_id,
                conversation_id=conversation_id,
                character_id=character_id,
                memory_type=MemoryType.EPISODIC,
                content=ep_data.get("event", ""),
                tags=ep_data.get("tags", []),
                entities={
                    "participants": ep_data.get("participants", []),
                    "emotion": ep_data.get("emotion", ""),
                },
                importance_score=importance,
            )
            self.db.add(entry)
            entries.append(entry)

        await self.db.flush()
        return entries

    async def get_recent_episodes(
        self,
        user_id: UUID,
        limit: int = 10,
        character_id: UUID | None = None,
    ) -> list[MemoryEntry]:
        stmt = (
            select(MemoryEntry)
            .where(
                MemoryEntry.user_id == user_id,
                MemoryEntry.memory_type == MemoryType.EPISODIC,
                MemoryEntry.is_archived == False,
            )
            .order_by(MemoryEntry.created_at.desc())
            .limit(limit)
        )
        if character_id:
            stmt = stmt.where(MemoryEntry.character_id == character_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_participant(
        self, user_id: UUID, participant_name: str, limit: int = 5
    ) -> list[MemoryEntry]:
        stmt = (
            select(MemoryEntry)
            .where(
                MemoryEntry.user_id == user_id,
                MemoryEntry.memory_type == MemoryType.EPISODIC,
                MemoryEntry.is_archived == False,
            )
            .order_by(MemoryEntry.importance_score.desc())
            .limit(limit * 3)
        )
        result = await self.db.execute(stmt)
        entries = result.scalars().all()

        return [
            e
            for e in entries
            if participant_name.lower()
            in str(e.entities.get("participants", [])).lower()
        ][:limit]
