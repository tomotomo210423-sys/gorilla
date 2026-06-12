"""
BGE-M3 embedder: produces dense + sparse embeddings simultaneously.
Enables true hybrid search without a separate BM25 index.
"""

import asyncio
from functools import lru_cache
from typing import Any
import structlog

logger = structlog.get_logger()


class BGEM3Embedder:
    """
    Wraps FlagEmbedding's BGEM3FlagModel for async usage.
    Returns both dense (1024-dim) and sparse (lexical) embeddings.
    """

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu", batch_size: int = 32):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None
        self._lock = asyncio.Lock()

    async def _ensure_model(self):
        if self._model is not None:
            return
        async with self._lock:
            if self._model is not None:
                return
            logger.info("loading_embedder", model=self.model_name, device=self.device)
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=(self.device == "cuda"),
                device=self.device,
            )
            logger.info("embedder_loaded")

    async def embed(self, texts: list[str]) -> dict[str, Any]:
        """Returns {"dense": [...], "sparse": [{"indices": [...], "values": [...]}]}"""
        await self._ensure_model()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                texts,
                batch_size=self.batch_size,
                max_length=512,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            ),
        )

        dense_embeddings = result["dense_vecs"].tolist()
        sparse_embeddings = []
        for lexical_weights in result["lexical_weights"]:
            indices = list(lexical_weights.keys())
            values = list(lexical_weights.values())
            sparse_embeddings.append({"indices": indices, "values": values})

        return {"dense": dense_embeddings, "sparse": sparse_embeddings}

    async def embed_query(self, query: str) -> dict[str, Any]:
        result = await self.embed([query])
        return {
            "dense": result["dense"][0],
            "sparse": result["sparse"][0],
        }
