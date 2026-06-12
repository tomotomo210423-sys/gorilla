"""
Semantic Memory: Structured knowledge and facts stored in Qdrant.
Uses BGE-M3 hybrid embeddings (dense + sparse) for superior retrieval.
"""

import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SparseVectorParams,
    SparseIndexParams,
    NamedVector,
    NamedSparseVector,
    SparseVector,
    QueryRequest,
    Prefetch,
    FusionQuery,
    Fusion,
)

from app.config import get_settings

logger = structlog.get_logger()

COLLECTION_NAME = "semantic_memory"
DENSE_DIM = 1024  # BGE-M3 dense dimension


@dataclass
class SemanticSearchResult:
    id: str
    content: str
    score: float
    metadata: dict[str, Any]


class SemanticMemory:
    def __init__(self, qdrant: AsyncQdrantClient, embedder: Any):
        self.qdrant = qdrant
        self.embedder = embedder
        self.settings = get_settings()

    async def initialize_collection(self) -> None:
        collections = await self.qdrant.get_collections()
        existing = [c.name for c in collections.collections]

        if COLLECTION_NAME not in existing:
            await self.qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config={
                    "dense": VectorParams(size=DENSE_DIM, distance=Distance.COSINE)
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
                },
            )
            logger.info("semantic_collection_created", name=COLLECTION_NAME)

    async def store(
        self,
        content: str,
        user_id: str,
        metadata: dict | None = None,
        point_id: str | None = None,
    ) -> str:
        point_id = point_id or str(uuid.uuid4())
        embeddings = await self._embed([content])

        point = PointStruct(
            id=point_id,
            vector={
                "dense": embeddings["dense"][0],
                "sparse": SparseVector(
                    indices=embeddings["sparse"][0]["indices"],
                    values=embeddings["sparse"][0]["values"],
                ),
            },
            payload={
                "content": content,
                "user_id": user_id,
                **(metadata or {}),
            },
        )

        await self.qdrant.upsert(collection_name=COLLECTION_NAME, points=[point])
        return point_id

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int | None = None,
        filters: dict | None = None,
    ) -> list[SemanticSearchResult]:
        top_k = top_k or self.settings.rag_top_k
        embeddings = await self._embed([query])

        must_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]
        if filters:
            for key, value in filters.items():
                must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        qdrant_filter = Filter(must=must_conditions)

        # Hybrid search: dense + sparse with RRF fusion
        results = await self.qdrant.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                Prefetch(
                    query=embeddings["dense"][0],
                    using="dense",
                    limit=top_k * 2,
                    filter=qdrant_filter,
                ),
                Prefetch(
                    query=SparseVector(
                        indices=embeddings["sparse"][0]["indices"],
                        values=embeddings["sparse"][0]["values"],
                    ),
                    using="sparse",
                    limit=top_k * 2,
                    filter=qdrant_filter,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )

        return [
            SemanticSearchResult(
                id=str(r.id),
                content=r.payload.get("content", ""),
                score=r.score,
                metadata={k: v for k, v in r.payload.items() if k != "content"},
            )
            for r in results.points
        ]

    async def delete(self, point_id: str) -> None:
        await self.qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=[point_id],
        )

    async def _embed(self, texts: list[str]) -> dict:
        """Returns dense and sparse embeddings via BGE-M3."""
        return await self.embedder.embed(texts)
