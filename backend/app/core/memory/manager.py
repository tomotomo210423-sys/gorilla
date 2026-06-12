"""
Memory Manager: Coordinates all 4 memory layers.
Handles memory lifecycle, context building, and learning from conversations.
"""

from uuid import UUID
from dataclasses import dataclass
import structlog

from .stm import ShortTermMemory, STMMessage
from .ltm import LongTermMemory
from .semantic import SemanticMemory
from .episodic import EpisodicMemory
from app.config import get_settings

logger = structlog.get_logger()


@dataclass
class MemoryContext:
    """Assembled memory context for prompt construction."""
    stm_messages: list[STMMessage]
    ltm_summaries: list[str]
    semantic_facts: list[str]
    episodic_events: list[str]
    user_profile: dict


class MemoryManager:
    def __init__(
        self,
        stm: ShortTermMemory,
        ltm: LongTermMemory,
        semantic: SemanticMemory,
        episodic: EpisodicMemory,
    ):
        self.stm = stm
        self.ltm = ltm
        self.semantic = semantic
        self.episodic = episodic
        self.settings = get_settings()

    async def add_turn(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        turn_index: int,
    ) -> None:
        await self.stm.add_message(conversation_id, role, content, turn_index)

        # Trigger LTM summarization when STM is full
        if await self.stm.needs_summarization(conversation_id):
            messages = await self.stm.get_messages(conversation_id)
            msg_dicts = [{"role": m.role, "content": m.content} for m in messages]

            await self.ltm.store_summary(
                user_id=UUID(user_id),
                conversation_id=UUID(conversation_id),
                messages=msg_dicts,
            )
            await self.episodic.extract_and_store(
                user_id=UUID(user_id),
                conversation_id=UUID(conversation_id),
                messages=msg_dicts,
            )
            # Also store in semantic memory for future RAG retrieval
            combined = " ".join(m["content"] for m in msg_dicts[-4:])
            await self.semantic.store(
                content=combined,
                user_id=user_id,
                metadata={"type": "conversation_segment", "conversation_id": conversation_id},
            )

            await self.stm.clear(conversation_id)
            logger.info("memory_consolidated", conversation_id=conversation_id)

    async def build_context(
        self,
        conversation_id: str,
        user_id: str,
        query: str,
        character_id: str | None = None,
    ) -> MemoryContext:
        uid = UUID(user_id)
        cid = UUID(character_id) if character_id else None

        stm_messages = await self.stm.get_messages(conversation_id)
        ltm_entries = await self.ltm.get_relevant_memories(uid, limit=3, character_id=cid)
        semantic_results = await self.semantic.search(
            query=query,
            user_id=user_id,
            top_k=self.settings.rag_rerank_top_k,
        )
        episodic_entries = await self.episodic.get_recent_episodes(uid, limit=3, character_id=cid)

        return MemoryContext(
            stm_messages=stm_messages,
            ltm_summaries=[e.content for e in ltm_entries],
            semantic_facts=[r.content for r in semantic_results],
            episodic_events=[e.content for e in episodic_entries],
            user_profile={},
        )

    async def learn_from_conversation(
        self,
        user_id: str,
        messages: list[dict],
        user_profile: dict,
    ) -> dict:
        """
        Extract user preferences, interests, and communication style from messages.
        Returns updated profile dict.
        """
        from app.core.llm.base import LLMMessage, GenerationConfig

        if len(messages) < 3:
            return user_profile

        LEARN_PROMPT = """以下の会話からユーザーの特徴を学習してください。

会話:
{conversation}

現在のユーザープロフィール:
{profile}

以下のJSON形式で更新されたプロフィールを出力してください:
{{
  "interests": ["興味・関心"],
  "communication_style": "会話スタイルの説明",
  "vocabulary_level": "語彙レベル（casual/standard/formal）",
  "frequent_topics": ["よく話す話題"],
  "preferences": {{"好み1": "値1"}},
  "personality_traits": ["性格的特徴"]
}}"""

        import json

        conversation_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in messages[-10:]
        )
        return user_profile
