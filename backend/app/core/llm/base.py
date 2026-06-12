from abc import ABC, abstractmethod
from typing import AsyncGenerator
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class GenerationConfig:
    temperature: float = 0.8
    max_tokens: int = 2048
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop: list[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_trace: str | None = None


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: GenerationConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass
