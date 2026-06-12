import json
from typing import AsyncGenerator
import httpx
import structlog

from .base import BaseLLMClient, GenerationConfig, GenerationResult, LLMMessage
from app.config import get_settings

logger = structlog.get_logger()


class OllamaClient(BaseLLMClient):
    """
    Ollama client using the OpenAI-compatible /v1/chat/completions endpoint.
    Supports streaming, function calling, and all standard parameters.
    """

    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.base_url = settings.ollama_url
        self.model = model or settings.default_model
        self.fallback_model = settings.fallback_model
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(settings.stream_timeout, connect=10.0),
        )

    async def generate(
        self,
        messages: list[LLMMessage],
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        config = config or GenerationConfig()
        payload = self._build_payload(messages, config, stream=False)

        try:
            response = await self._client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            return GenerationResult(
                content=choice["message"]["content"],
                model=data["model"],
                prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
            )
        except httpx.HTTPStatusError as e:
            logger.error("ollama_generate_error", status=e.response.status_code, model=self.model)
            raise

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: GenerationConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        config = config or GenerationConfig()
        payload = self._build_payload(messages, config, stream=True)

        async with self._client.stream("POST", "/v1/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    if content := delta.get("content"):
                        yield content
                except (json.JSONDecodeError, KeyError):
                    continue

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        response = await self._client.get("/api/tags")
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]

    async def pull_model(self, model_name: str) -> AsyncGenerator[str, None]:
        async with self._client.stream(
            "POST", "/api/pull", json={"name": model_name}
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if status := data.get("status"):
                            yield status
                    except json.JSONDecodeError:
                        continue

    def _build_payload(
        self, messages: list[LLMMessage], config: GenerationConfig, stream: bool
    ) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stop": config.stop or None,
            "options": {
                "repeat_penalty": config.repeat_penalty,
                "top_k": config.top_k,
            },
        }

    async def aclose(self):
        await self._client.aclose()
