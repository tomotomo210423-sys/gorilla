"""
Gorilla AI - Advanced Personal AI Assistant
Main FastAPI application with lifespan management.
"""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from qdrant_client import AsyncQdrantClient

from app.config import get_settings
from app.models import Base
from app.db.session import engine
from app.core.llm.ollama import OllamaClient
from app.core.memory.stm import ShortTermMemory
from app.core.memory.ltm import LongTermMemory
from app.core.memory.semantic import SemanticMemory
from app.core.memory.episodic import EpisodicMemory
from app.core.memory.manager import MemoryManager
from app.core.rag.embedder import BGEM3Embedder
from app.core.rag.pipeline import RAGPipeline, BGEReranker
from app.core.reasoning.adaptive import AdaptiveReasoner
from app.core.orchestrator import Orchestrator
from app.api import chat, memory, character, knowledge

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_gorilla_ai", model=settings.default_model)

    # Initialize database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_initialized")

    # Initialize infrastructure clients
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    # Initialize embedding model
    embedder = BGEM3Embedder(
        model_name=settings.embed_model,
        device=settings.embed_device,
        batch_size=settings.embed_batch_size,
    )

    # Initialize LLM
    llm = OllamaClient(model=settings.default_model)
    llm_health = await llm.health_check()
    if not llm_health:
        logger.warning("ollama_not_available", url=settings.ollama_url)

    # Initialize memory layers (DB session for LTM/Episodic created per-request)
    stm = ShortTermMemory(redis=redis)

    # Initialize Qdrant collections
    from app.core.memory.semantic import SemanticMemory, COLLECTION_NAME

    semantic_memory_for_init = SemanticMemory(qdrant=qdrant, embedder=embedder)
    await semantic_memory_for_init.initialize_collection()

    # Initialize RAG
    reranker = BGEReranker(model_name=settings.reranker_model)
    rag_pipeline = RAGPipeline(
        embedder=embedder,
        semantic_memory=semantic_memory_for_init,
        reranker=reranker,
    )

    # Initialize reasoning
    reasoner = AdaptiveReasoner(llm=llm)

    # Build stateless orchestrator factory (per-request gets fresh DB session)
    from app.db.session import AsyncSessionLocal

    async def create_orchestrator():
        async with AsyncSessionLocal() as db:
            semantic = SemanticMemory(qdrant=qdrant, embedder=embedder)
            ltm = LongTermMemory(db=db, llm=llm)
            episodic = EpisodicMemory(db=db, llm=llm)
            memory_manager = MemoryManager(stm=stm, ltm=ltm, semantic=semantic, episodic=episodic)
            return Orchestrator(
                memory_manager=memory_manager,
                rag_pipeline=rag_pipeline,
                reasoner=reasoner,
            )

    app.state.orchestrator_factory = create_orchestrator
    app.state.rag_pipeline = rag_pipeline
    app.state.redis = redis
    app.state.qdrant = qdrant
    app.state.llm = llm

    # For simple dependency injection, create a shared orchestrator
    # In production, use per-request orchestrators with proper session management
    app.state.orchestrator = Orchestrator(
        memory_manager=MemoryManager(
            stm=stm,
            ltm=None,
            semantic=semantic_memory_for_init,
            episodic=None,
        ),
        rag_pipeline=rag_pipeline,
        reasoner=reasoner,
    )

    logger.info("gorilla_ai_ready")
    yield

    # Cleanup
    await redis.aclose()
    await qdrant.close()
    await llm.aclose()
    logger.info("gorilla_ai_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gorilla AI",
        description="Advanced Personal AI Assistant with Memory, RAG, and Character Systems",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router)
    app.include_router(memory.router)
    app.include_router(character.router)
    app.include_router(knowledge.router)

    @app.get("/health")
    async def health() -> dict:
        llm_ok = await app.state.llm.health_check()
        return {
            "status": "ok",
            "llm": "ok" if llm_ok else "unavailable",
            "model": settings.default_model,
        }

    return app


app = create_app()
