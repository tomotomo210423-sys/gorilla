from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    app_name: str = "Gorilla AI"
    secret_key: str = Field(default="change-in-production-please", min_length=32)
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://gorilla:gorilla_secret@localhost:5432/gorilla_ai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # LLM (Ollama compatible)
    ollama_url: str = "http://localhost:11434"
    default_model: str = "qwen2.5:14b"
    fallback_model: str = "qwen2.5:7b"

    # Embedding
    embed_model: str = "BAAI/bge-m3"
    embed_device: str = "cpu"  # "cuda" for GPU
    embed_batch_size: int = 32

    # Reranker
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_top_k: int = 5

    # Memory settings
    stm_max_turns: int = 20
    stm_ttl_seconds: int = 86400  # 24 hours
    ltm_summary_threshold: int = 10  # Summarize every N turns
    memory_importance_threshold: float = 0.3
    forgetting_lambda: float = 0.1  # Ebbinghaus decay rate

    # RAG
    rag_top_k: int = 10
    rag_rerank_top_k: int = 5
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64

    # Context window management
    max_context_tokens: int = 8192
    character_prompt_reserve: int = 2048
    stm_token_reserve: int = 3072
    rag_token_reserve: int = 2048

    # Generation
    default_temperature: float = 0.8
    default_max_tokens: int = 2048
    stream_timeout: int = 120

    # Reasoning
    cot_threshold: float = 0.6  # Complexity score above which CoT is triggered
    reflection_threshold: float = 0.85

    # Character
    emotion_decay_rate: float = 0.3  # How fast emotions return to baseline


@lru_cache
def get_settings() -> Settings:
    return Settings()
