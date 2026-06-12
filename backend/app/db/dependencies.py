"""
FastAPI dependency injection for core services.
Services are initialized once at startup and reused across requests.
"""

from functools import lru_cache
from fastapi import Request

from app.core.orchestrator import Orchestrator
from app.core.rag.pipeline import RAGPipeline


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def get_rag_pipeline(request: Request) -> RAGPipeline:
    return request.app.state.rag_pipeline
