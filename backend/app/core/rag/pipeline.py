"""
RAG Pipeline: Document ingestion, chunking, retrieval, reranking.
Uses BGE-M3 hybrid search + BGE-Reranker for maximum retrieval quality.
"""

import re
import uuid
from dataclasses import dataclass
from typing import Any
import structlog

from .embedder import BGEM3Embedder
from app.core.memory.semantic import SemanticMemory
from app.config import get_settings

logger = structlog.get_logger()


@dataclass
class RAGResult:
    content: str
    source: str
    score: float
    metadata: dict[str, Any]


class DocumentChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, source: str = "") -> list[dict]:
        sentences = re.split(r"(?<=[。！？\.\!\?])\s*", text)
        chunks = []
        current_chunk = []
        current_len = 0

        for sentence in sentences:
            if not sentence.strip():
                continue
            sent_len = len(sentence)

            if current_len + sent_len > self.chunk_size and current_chunk:
                chunk_text = "".join(current_chunk)
                chunks.append({"content": chunk_text, "source": source})

                overlap_text = "".join(current_chunk[-2:])
                current_chunk = [overlap_text] if len(overlap_text) < self.chunk_overlap else []
                current_len = len("".join(current_chunk))

            current_chunk.append(sentence)
            current_len += sent_len

        if current_chunk:
            chunks.append({"content": "".join(current_chunk), "source": source})

        return chunks


class BGEReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None

    async def _ensure_model(self):
        if self._model is not None:
            return
        import asyncio
        from FlagEmbedding import FlagReranker

        loop = asyncio.get_event_loop()
        self._model = await loop.run_in_executor(
            None, lambda: FlagReranker(self.model_name, use_fp16=False)
        )
        logger.info("reranker_loaded", model=self.model_name)

    async def rerank(
        self, query: str, results: list[RAGResult], top_k: int = 5
    ) -> list[RAGResult]:
        if not results:
            return []

        await self._ensure_model()
        import asyncio

        pairs = [[query, r.content] for r in results]
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            None, lambda: self._model.compute_score(pairs, normalize=True)
        )

        scored = sorted(zip(scores, results), key=lambda x: x[0], reverse=True)
        reranked = []
        for score, result in scored[:top_k]:
            result.score = float(score)
            reranked.append(result)

        return reranked


class RAGPipeline:
    def __init__(
        self,
        embedder: BGEM3Embedder,
        semantic_memory: SemanticMemory,
        reranker: BGEReranker | None = None,
    ):
        self.embedder = embedder
        self.semantic_memory = semantic_memory
        self.reranker = reranker
        self.chunker = DocumentChunker(
            chunk_size=get_settings().rag_chunk_size,
            chunk_overlap=get_settings().rag_chunk_overlap,
        )
        self.settings = get_settings()

    async def ingest_document(
        self,
        text: str,
        user_id: str,
        source: str = "",
        metadata: dict | None = None,
    ) -> list[str]:
        chunks = self.chunker.chunk(text, source)
        point_ids = []

        for chunk in chunks:
            meta = {"source": source, "type": "document", **(metadata or {})}
            point_id = await self.semantic_memory.store(
                content=chunk["content"],
                user_id=user_id,
                metadata=meta,
            )
            point_ids.append(point_id)

        logger.info("document_ingested", chunks=len(chunks), source=source)
        return point_ids

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int | None = None,
        use_reranker: bool = True,
    ) -> list[RAGResult]:
        top_k = top_k or self.settings.rag_top_k

        raw_results = await self.semantic_memory.search(
            query=query,
            user_id=user_id,
            top_k=top_k * 2 if use_reranker else top_k,
        )

        results = [
            RAGResult(
                content=r.content,
                source=r.metadata.get("source", ""),
                score=r.score,
                metadata=r.metadata,
            )
            for r in raw_results
        ]

        if use_reranker and self.reranker and results:
            results = await self.reranker.rerank(
                query=query,
                results=results,
                top_k=self.settings.rag_rerank_top_k,
            )

        return results

    def format_context(self, results: list[RAGResult]) -> str:
        if not results:
            return ""
        parts = []
        for i, r in enumerate(results, 1):
            source_label = f"[出典: {r.source}]" if r.source else f"[知識 {i}]"
            parts.append(f"{source_label}\n{r.content}")
        return "\n\n".join(parts)
