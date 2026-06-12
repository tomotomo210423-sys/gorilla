"""
Long Term Memory: LLM-summarized conversation segments + important facts.
Stored in PostgreSQL for structured queries and Qdrant for semantic search.
"""

import math
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.memory import MemoryEntry, MemoryType
from app.config import get_settings
from app.core.llm.base import BaseLLMClient, LLMMessage, GenerationConfig

logger = structlog.get_logger()

SUMMARIZATION_PROMPT = """以下の会話セグメントを分析し、重要な情報を抽出してください。

会話:
{conversation}

以下のJSON形式で出力してください:
{{
  "summary": "会話の簡潔な要約（200字以内）",
  "key_facts": ["重要な事実1", "重要な事実2"],
  "entities": {{
    "persons": ["言及された人物"],
    "places": ["場所"],
    "events": ["出来事"]
  }},
  "importance_score": 0.0から1.0（会話の重要度）,
  "topics": ["話題1", "話題2"]
}}"""


class LongTermMemory:
    def __init__(self, db: AsyncSession, llm: BaseLLMClient):
        self.db = db
        self.llm = llm
        self.settings = get_settings()

    async def store_summary(
        self,
        user_id: UUID,
        conversation_id: UUID,
        messages: list[dict],
        character_id: UUID | None = None,
    ) -> MemoryEntry | None:
        if not messages:
            return None

        conversation_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in messages
        )

        try:
            result = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="user",
                        content=SUMMARIZATION_PROMPT.format(conversation=conversation_text),
                    )
                ],
                config=GenerationConfig(temperature=0.3, max_tokens=512),
            )
            import json

            data = json.loads(result.content)
        except Exception as e:
            logger.error("ltm_summarization_failed", error=str(e))
            data = {
                "summary": conversation_text[:200],
                "key_facts": [],
                "entities": {},
                "importance_score": 0.5,
                "topics": [],
            }

        entry = MemoryEntry(
            user_id=user_id,
            conversation_id=conversation_id,
            character_id=character_id,
            memory_type=MemoryType.LONG_TERM,
            content=data.get("summary", ""),
            tags=data.get("topics", []),
            entities=data.get("entities", {}),
            importance_score=float(data.get("importance_score", 0.5)),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_relevant_memories(
        self,
        user_id: UUID,
        limit: int = 5,
        character_id: UUID | None = None,
    ) -> list[MemoryEntry]:
        stmt = (
            select(MemoryEntry)
            .where(
                MemoryEntry.user_id == user_id,
                MemoryEntry.memory_type == MemoryType.LONG_TERM,
                MemoryEntry.is_archived == False,
            )
            .order_by(MemoryEntry.retention_score.desc(), MemoryEntry.created_at.desc())
            .limit(limit)
        )
        if character_id:
            stmt = stmt.where(MemoryEntry.character_id == character_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def apply_forgetting_curve(self, user_id: UUID) -> int:
        """
        Ebbinghaus forgetting curve: retention = importance × e^(-λt) × log(1 + access_count)
        Updates retention scores and archives entries below threshold.
        """
        stmt = select(MemoryEntry).where(
            MemoryEntry.user_id == user_id,
            MemoryEntry.is_archived == False,
        )
        result = await self.db.execute(stmt)
        entries = list(result.scalars().all())
        archived = 0

        now = datetime.now(timezone.utc)
        lam = self.settings.forgetting_lambda

        for entry in entries:
            days_elapsed = (now - entry.created_at).days
            recency_decay = math.exp(-lam * days_elapsed)
            frequency_boost = math.log1p(entry.access_count)
            retention = entry.importance_score * recency_decay * (1 + 0.1 * frequency_boost)

            if retention < 0.01:
                entry.is_archived = True
                archived += 1
            else:
                entry.retention_score = retention

        await self.db.flush()
        return archived

    async def record_access(self, memory_id: UUID) -> None:
        stmt = (
            update(MemoryEntry)
            .where(MemoryEntry.id == memory_id)
            .values(access_count=MemoryEntry.access_count + 1)
        )
        await self.db.execute(stmt)
