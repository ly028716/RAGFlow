"""Local knowledge-base retrieval tool for the RAG Agent.

This tool deliberately delegates retrieval to :class:`RetrievalService` and
does not expose any web/search client.  It returns citation-ready JSON so the
Agent UI can render the same source information as the regular RAG chain.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Type

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.vector_store import get_vector_store_manager
from app.services.rag.retrieval_service import RetrievalService


class KnowledgeBaseSearchInput(BaseModel):
    """Arguments accepted by the local knowledge-base search tool."""

    query: str = Field(..., min_length=1, description="要检索的问题或关键词")
    knowledge_base_ids: List[int] = Field(
        ..., min_length=1, description="允许检索的知识库 ID 列表"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="最多返回的片段数量")


class KnowledgeBaseSearchTool(BaseTool):
    """Search only local Chroma knowledge bases and return citation metadata."""

    name: str = "knowledge_base_search"
    description: str = (
        "仅检索本地知识库中的文档片段，不访问互联网。"
        "输入 query、knowledge_base_ids 和可选 top_k，返回带来源和相似度的引用片段。"
    )
    args_schema: Type[BaseModel] = KnowledgeBaseSearchInput
    allowed_knowledge_base_ids: List[int] = Field(default_factory=list, exclude=True)

    @staticmethod
    def _serialize(query: str, results: List[tuple], retrieval_time_ms: float = 0.0) -> str:
        citations: List[Dict[str, Any]] = []
        for document, similarity in results:
            metadata = document.metadata or {}
            citations.append(
                {
                    "knowledge_base_id": metadata.get("knowledge_base_id"),
                    "document_id": metadata.get("document_id"),
                    "chunk_index": metadata.get("chunk_index"),
                    "content": document.page_content,
                    "document_name": metadata.get("source")
                    or metadata.get("file_path")
                    or metadata.get("document_name")
                    or "Unknown",
                    "similarity_score": similarity,
                }
            )
        return json.dumps(
            {
                "query": query,
                "count": len(citations),
                "results": citations,
                "retrieval_time_ms": retrieval_time_ms,
            },
            ensure_ascii=False,
        )

    async def _search(
        self, query: str, knowledge_base_ids: List[int], top_k: int
    ) -> str:
        if not set(knowledge_base_ids).issubset(set(self.allowed_knowledge_base_ids)):
            return json.dumps(
                {"query": query, "count": 0, "results": [], "error": "知识库不在当前授权范围内"},
                ensure_ascii=False,
            )
        service = RetrievalService(get_vector_store_manager())
        started = time.perf_counter()
        results = await service.retrieve(knowledge_base_ids, query, top_k)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return self._serialize(query, results, elapsed_ms)

    def _run(
        self,
        query: str,
        knowledge_base_ids: List[int],
        top_k: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return asyncio.run(self._search(query, knowledge_base_ids, top_k))

    async def _arun(
        self,
        query: str,
        knowledge_base_ids: List[int],
        top_k: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return await self._search(query, knowledge_base_ids, top_k)


__all__ = ["KnowledgeBaseSearchInput", "KnowledgeBaseSearchTool"]
