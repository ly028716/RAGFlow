import pytest
from langchain_core.documents import Document

from app.services.rag.retrieval_service import RetrievalService


class FakeVectorStore:
    async def similarity_search_with_score(self, knowledge_base_id, query, k=5):
        return [
            (
                Document(
                    page_content="keep",
                    metadata={"knowledge_base_id": 1, "document_id": 1, "chunk_index": 0},
                ),
                0.1,
            ),
            (
                Document(
                    page_content="duplicate",
                    metadata={"knowledge_base_id": 1, "document_id": 2, "chunk_index": 0},
                ),
                0.2,
            ),
            (
                Document(
                    page_content="duplicate",
                    metadata={"knowledge_base_id": 1, "document_id": 2, "chunk_index": 0},
                ),
                0.2,
            ),
            (
                Document(
                    page_content="low",
                    metadata={"knowledge_base_id": 1, "document_id": 3, "chunk_index": 0},
                ),
                1.8,
            ),
        ]


@pytest.mark.asyncio
async def test_retrieval_filters_sorts_and_deduplicates(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings.rag, "rag_similarity_threshold", 0.7)
    service = RetrievalService(FakeVectorStore())
    results = await service.retrieve([1], "question", top_k=5)
    assert [doc.page_content for doc, _ in results] == ["keep", "duplicate"]
    assert results[0][1] > results[1][1]


@pytest.mark.asyncio
async def test_retrieval_returns_empty_for_missing_knowledge_base():
    service = RetrievalService(FakeVectorStore())
    assert await service.retrieve([], "question", top_k=5) == []
