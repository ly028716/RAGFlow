"""Unified local-vector retrieval for the RAG pipeline.

The service deliberately owns score normalization, threshold filtering and
deduplication so every API entry point observes the same retrieval semantics.
"""

import math
from typing import Any, List, Optional

from app.config import settings
from app.core.vector_store import VectorStoreManager


def distance_to_similarity(distance: Any) -> float:
    """Convert Chroma distance to a bounded similarity score."""
    try:
        value = float(distance)
    except (TypeError, ValueError):
        return 0.0
    if value < 0:
        return 0.0
    if value <= 2.0:
        return max(0.0, min(1.0, 1.0 - value / 2.0))
    return 1.0 / (1.0 + math.sqrt(value))


class RetrievalService:
    """Retrieve and normalize chunks from one or more local Chroma stores."""

    def __init__(
        self,
        vector_store_manager: VectorStoreManager,
        similarity_threshold: Optional[float] = None,
    ) -> None:
        self.vector_store_manager = vector_store_manager
        self.similarity_threshold = (
            settings.rag.rag_similarity_threshold
            if similarity_threshold is None
            else similarity_threshold
        )

    async def retrieve(
        self,
        knowledge_base_ids: List[int],
        query: str,
        top_k: int,
    ) -> List[tuple]:
        """Return ``(Document, similarity)`` tuples after filtering/deduping."""
        if not knowledge_base_ids or not query.strip() or top_k <= 0:
            return []
        fetch_k = max(top_k, top_k * 2)
        if len(knowledge_base_ids) == 1:
            raw = await self.vector_store_manager.similarity_search_with_score(
                knowledge_base_id=knowledge_base_ids[0], query=query, k=fetch_k
            )
        else:
            raw = await self.vector_store_manager.multi_knowledge_base_search(
                knowledge_base_ids=knowledge_base_ids, query=query, k=fetch_k
            )

        selected = []
        seen = set()
        for document, distance in raw:
            similarity = distance_to_similarity(distance)
            if similarity < self.similarity_threshold:
                continue
            metadata = document.metadata or {}
            key = (
                metadata.get("document_id"),
                metadata.get("chunk_index"),
                metadata.get("source"),
                document.page_content,
            )
            if key in seen:
                continue
            seen.add(key)
            selected.append((document, round(similarity, 6)))
        selected.sort(key=lambda item: item[1], reverse=True)
        return selected[:top_k]


__all__ = ["RetrievalService", "distance_to_similarity"]
