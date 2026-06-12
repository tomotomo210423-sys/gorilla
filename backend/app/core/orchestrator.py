"""
Orchestrator: The central coordinator of the AI system.
Assembles context from all memory layers and character state,
builds the final prompt, and routes through adaptive reasoning.
"""

from typing import AsyncGenerator
from uuid import UUID
import structlog

from app.core.llm.base import LLMMessage, GenerationConfig, GenerationResult
from app.core.memory.manager import MemoryManager
from app.core.rag.pipeline import RAGPipeline
from app.core.character.profile import CharacterStateManager
from app.core.reasoning.adaptive import AdaptiveReasoner
from app.config import get_settings

logger = structlog.get_logger()


def _count_tokens_approx(text: str) -> int:
    """Approximate token count: ~1 token per 2 Japanese chars or 4 English chars."""
    return len(text) // 2


class ContextBuilder:
    """Assembles the final message list respecting token budget."""

    def __init__(self, max_tokens: int = 8192):
        self.max_tokens = max_tokens
        self.settings = get_settings()

    def build(
        self,
        system_prompt: str,
        stm_messages: list,
        ltm_summaries: list[str],
        semantic_facts: list[str],
        episodic_events: list[str],
        rag_results: list[str],
        user_query: str,
    ) -> list[LLMMessage]:
        messages = []
        token_budget = self.max_tokens

        # 1. System prompt (always included)
        system_content = system_prompt
        token_budget -= _count_tokens_approx(system_content)

        # 2. Long-term memories
        if ltm_summaries and token_budget > 500:
            ltm_text = "\n\n【過去の会話から記憶していること】\n" + "\n".join(
                f"- {s}" for s in ltm_summaries[:3]
            )
            if _count_tokens_approx(ltm_text) < token_budget // 3:
                system_content += "\n\n" + ltm_text
                token_budget -= _count_tokens_approx(ltm_text)

        # 3. Episodic memories
        if episodic_events and token_budget > 400:
            ep_text = "\n【記憶しているエピソード】\n" + "\n".join(
                f"- {e}" for e in episodic_events[:3]
            )
            if _count_tokens_approx(ep_text) < token_budget // 4:
                system_content += "\n" + ep_text
                token_budget -= _count_tokens_approx(ep_text)

        # 4. RAG context
        if rag_results and token_budget > 600:
            rag_text = "\n\n【参考知識】\n" + "\n\n".join(rag_results[:3])
            if _count_tokens_approx(rag_text) < token_budget // 3:
                system_content += "\n\n" + rag_text
                token_budget -= _count_tokens_approx(rag_text)

        messages.append(LLMMessage(role="system", content=system_content))

        # 5. STM (recent conversation history)
        stm_token_budget = min(token_budget - 512, self.settings.stm_token_reserve)
        included_stm = []
        stm_tokens = 0
        for msg in reversed(stm_messages):
            t = _count_tokens_approx(msg.content)
            if stm_tokens + t > stm_token_budget:
                break
            included_stm.insert(0, msg)
            stm_tokens += t

        for msg in included_stm:
            messages.append(LLMMessage(role=msg.role, content=msg.content))

        # 6. Current user query
        messages.append(LLMMessage(role="user", content=user_query))
        return messages


class Orchestrator:
    def __init__(
        self,
        memory_manager: MemoryManager,
        rag_pipeline: RAGPipeline,
        reasoner: AdaptiveReasoner,
        character_manager: CharacterStateManager | None = None,
    ):
        self.memory = memory_manager
        self.rag = rag_pipeline
        self.reasoner = reasoner
        self.character = character_manager
        self.context_builder = ContextBuilder()
        self.settings = get_settings()

    async def chat(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        config = config or GenerationConfig(
            temperature=self.settings.default_temperature,
            max_tokens=self.settings.default_max_tokens,
        )

        await self.memory.add_turn(
            conversation_id, user_id, "user", user_message, turn_index=0
        )

        context = await self.memory.build_context(
            conversation_id=conversation_id,
            user_id=user_id,
            query=user_message,
        )

        rag_results = await self.rag.retrieve(query=user_message, user_id=user_id)
        rag_texts = [r.content for r in rag_results]

        system_prompt = self._get_system_prompt(user_id)

        messages = self.context_builder.build(
            system_prompt=system_prompt,
            stm_messages=context.stm_messages,
            ltm_summaries=context.ltm_summaries,
            semantic_facts=context.semantic_facts,
            episodic_events=context.episodic_events,
            rag_results=rag_texts,
            user_query=user_message,
        )

        result = await self.reasoner.generate(messages, query=user_message, config=config)

        await self.memory.add_turn(
            conversation_id, user_id, "assistant", result.content, turn_index=1
        )

        return result

    async def chat_stream(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        config: GenerationConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        config = config or GenerationConfig(
            temperature=self.settings.default_temperature,
            max_tokens=self.settings.default_max_tokens,
        )

        await self.memory.add_turn(
            conversation_id, user_id, "user", user_message, turn_index=0
        )

        context = await self.memory.build_context(
            conversation_id=conversation_id,
            user_id=user_id,
            query=user_message,
        )

        rag_results = await self.rag.retrieve(query=user_message, user_id=user_id)
        rag_texts = [r.content for r in rag_results]
        system_prompt = self._get_system_prompt(user_id)

        messages = self.context_builder.build(
            system_prompt=system_prompt,
            stm_messages=context.stm_messages,
            ltm_summaries=context.ltm_summaries,
            semantic_facts=context.semantic_facts,
            episodic_events=context.episodic_events,
            rag_results=rag_texts,
            user_query=user_message,
        )

        full_response = []
        async for chunk in self.reasoner.generate_stream(messages, query=user_message, config=config):
            full_response.append(chunk)
            yield chunk

        response_text = "".join(full_response)
        await self.memory.add_turn(
            conversation_id, user_id, "assistant", response_text, turn_index=1
        )

    def _get_system_prompt(self, user_id: str) -> str:
        if self.character:
            return self.character.build_system_prompt()
        return (
            "あなたは親切で知識豊富なAIアシスタントです。"
            "ユーザーの質問に対して正確で丁寧な回答を提供してください。"
            "長い会話を通じてユーザーのことを覚え、パーソナライズされた応答を心がけてください。"
        )
