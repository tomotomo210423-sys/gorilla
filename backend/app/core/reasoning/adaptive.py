"""
Adaptive Reasoning: Automatically selects the appropriate reasoning strategy
based on query complexity. Avoids unnecessary overhead for simple queries.
"""

import re
from enum import Enum
from typing import AsyncGenerator
import structlog

from app.core.llm.base import BaseLLMClient, LLMMessage, GenerationConfig, GenerationResult
from app.config import get_settings

logger = structlog.get_logger()


class ReasoningMode(str, Enum):
    DIRECT = "direct"          # Simple chat: no extra overhead
    COT = "chain_of_thought"   # Medium complexity: think step by step
    REFLECTION = "reflection"  # High complexity: reflect and revise


COMPLEXITY_SIGNALS = {
    "high": [
        r"なぜ|why|理由|原因|仕組み|どうして",
        r"比較|違い|difference|compare",
        r"計画|plan|戦略|strategy",
        r"分析|analyze|evaluate|評価",
        r"証明|prove|論証",
        r"矛盾|contradiction|paradox",
        r"最適|optimal|best.*approach",
    ],
    "medium": [
        r"説明|explain|教え",
        r"方法|how to|やり方",
        r"問題|problem|issue|解決",
        r"意見|opinion|consider|考え",
    ],
}

COT_SYSTEM_ADDENDUM = """
問題に答える前に、以下の形式で思考プロセスを示してください:

<thinking>
1. 問題の分析
2. 関連する情報の整理
3. 解決アプローチの検討
</thinking>

<answer>
最終的な回答
</answer>
"""

REFLECTION_SYSTEM_ADDENDUM = """
以下のステップで回答してください:

<thinking>
問題の分析と初期アプローチ
</thinking>

<draft>
初期回答
</draft>

<reflection>
初期回答の問題点・改善点の検討
</reflection>

<answer>
改善された最終回答
</answer>
"""


def estimate_complexity(query: str) -> float:
    """Returns complexity score 0.0-1.0"""
    score = 0.0
    query_lower = query.lower()

    for pattern in COMPLEXITY_SIGNALS["high"]:
        if re.search(pattern, query_lower):
            score += 0.3

    for pattern in COMPLEXITY_SIGNALS["medium"]:
        if re.search(pattern, query_lower):
            score += 0.15

    # Length is a weak signal
    if len(query) > 200:
        score += 0.1
    elif len(query) > 100:
        score += 0.05

    return min(1.0, score)


def select_reasoning_mode(complexity: float, settings) -> ReasoningMode:
    if complexity >= settings.reflection_threshold:
        return ReasoningMode.REFLECTION
    elif complexity >= settings.cot_threshold:
        return ReasoningMode.COT
    return ReasoningMode.DIRECT


def extract_answer(content: str, mode: ReasoningMode) -> tuple[str, str | None]:
    """Returns (answer, reasoning_trace)"""
    if mode == ReasoningMode.DIRECT:
        return content, None

    answer_match = re.search(r"<answer>(.*?)</answer>", content, re.DOTALL)
    if answer_match:
        answer = answer_match.group(1).strip()
    else:
        answer = content

    thinking_match = re.search(r"<thinking>(.*?)</thinking>", content, re.DOTALL)
    reflection_match = re.search(r"<reflection>(.*?)</reflection>", content, re.DOTALL)
    trace_parts = []
    if thinking_match:
        trace_parts.append(f"[思考]\n{thinking_match.group(1).strip()}")
    if reflection_match:
        trace_parts.append(f"[省察]\n{reflection_match.group(1).strip()}")

    return answer, "\n\n".join(trace_parts) if trace_parts else None


class AdaptiveReasoner:
    def __init__(self, llm: BaseLLMClient):
        self.llm = llm
        self.settings = get_settings()

    def _augment_messages(
        self, messages: list[LLMMessage], mode: ReasoningMode
    ) -> list[LLMMessage]:
        if mode == ReasoningMode.DIRECT:
            return messages

        addendum = COT_SYSTEM_ADDENDUM if mode == ReasoningMode.COT else REFLECTION_SYSTEM_ADDENDUM

        augmented = []
        for msg in messages:
            if msg.role == "system":
                augmented.append(LLMMessage(role="system", content=msg.content + addendum))
            else:
                augmented.append(msg)
        return augmented

    async def generate(
        self,
        messages: list[LLMMessage],
        query: str,
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        complexity = estimate_complexity(query)
        mode = select_reasoning_mode(complexity, self.settings)

        logger.debug("reasoning_mode_selected", mode=mode, complexity=complexity)

        augmented = self._augment_messages(messages, mode)

        if mode in (ReasoningMode.COT, ReasoningMode.DIRECT):
            result = await self.llm.generate(augmented, config)
            answer, trace = extract_answer(result.content, mode)
            result.content = answer
            result.reasoning_trace = trace
            return result

        # REFLECTION: generate + self-check
        result = await self.llm.generate(augmented, config)
        answer, trace = extract_answer(result.content, mode)
        result.content = answer
        result.reasoning_trace = trace
        return result

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        query: str,
        config: GenerationConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        complexity = estimate_complexity(query)
        mode = select_reasoning_mode(complexity, self.settings)
        augmented = self._augment_messages(messages, mode)

        buffer = ""
        in_answer = False
        answer_started = False

        async for chunk in self.llm.generate_stream(augmented, config):
            buffer += chunk

            if mode == ReasoningMode.DIRECT:
                yield chunk
                continue

            if not answer_started and "<answer>" in buffer:
                answer_started = True
                idx = buffer.index("<answer>") + len("<answer>")
                buffer = buffer[idx:]
                in_answer = True

            if in_answer:
                if "</answer>" in buffer:
                    end_idx = buffer.index("</answer>")
                    yield buffer[:end_idx]
                    buffer = ""
                    in_answer = False
                else:
                    # Stream the answer content, hold back potential partial tags
                    safe = buffer[:-20] if len(buffer) > 20 else ""
                    if safe:
                        yield safe
                        buffer = buffer[len(safe):]
