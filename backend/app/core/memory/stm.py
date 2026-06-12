"""
Short Term Memory: Redis-backed conversation buffer.
Stores raw recent messages with automatic TTL expiry.
"""

import json
import uuid
from dataclasses import dataclass, asdict
from redis.asyncio import Redis
import structlog

from app.config import get_settings

logger = structlog.get_logger()


@dataclass
class STMMessage:
    role: str
    content: str
    turn_index: int
    message_id: str = ""


class ShortTermMemory:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.settings = get_settings()

    def _key(self, conversation_id: str) -> str:
        return f"stm:{conversation_id}"

    async def add_message(
        self, conversation_id: str, role: str, content: str, turn_index: int
    ) -> None:
        msg = STMMessage(
            role=role,
            content=content,
            turn_index=turn_index,
            message_id=str(uuid.uuid4()),
        )
        key = self._key(conversation_id)
        await self.redis.rpush(key, json.dumps(asdict(msg)))
        await self.redis.expire(key, self.settings.stm_ttl_seconds)

        # Trim to max_turns (keep last N)
        max_len = self.settings.stm_max_turns
        current_len = await self.redis.llen(key)
        if current_len > max_len:
            await self.redis.ltrim(key, current_len - max_len, -1)

    async def get_messages(self, conversation_id: str) -> list[STMMessage]:
        key = self._key(conversation_id)
        raw_messages = await self.redis.lrange(key, 0, -1)
        return [STMMessage(**json.loads(m)) for m in raw_messages]

    async def get_recent(self, conversation_id: str, n: int) -> list[STMMessage]:
        key = self._key(conversation_id)
        raw_messages = await self.redis.lrange(key, -n, -1)
        return [STMMessage(**json.loads(m)) for m in raw_messages]

    async def clear(self, conversation_id: str) -> None:
        await self.redis.delete(self._key(conversation_id))

    async def count(self, conversation_id: str) -> int:
        return await self.redis.llen(self._key(conversation_id))

    async def needs_summarization(self, conversation_id: str) -> bool:
        count = await self.count(conversation_id)
        return count >= self.settings.ltm_summary_threshold
