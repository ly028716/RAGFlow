"""Focused resilience and scope-isolation tests for local RAG."""

import pytest
from langchain_core.documents import Document

from app.services.rag.citation_service import CitationService
from app.services.rag.retrieval_service import RetrievalService


class _CrossScopeVectorStore:
    async def multi_knowledge_base_search(self, knowledge_base_ids, query, k):
        assert knowledge_base_ids == [11, 22]
        assert query == "deployment steps"
        return [
            (
                Document(
                    page_content="from kb 11",
                    metadata={"knowledge_base_id": 11, "document_id": 1, "chunk_index": 0},
                ),
                0.1,
            ),
            (
                Document(
                    page_content="unexpected kb 99",
                    metadata={"knowledge_base_id": 99, "document_id": 9, "chunk_index": 0},
                ),
                0.0,
            ),
            (
                Document(
                    page_content="from kb 22",
                    metadata={"knowledge_base_id": 22, "document_id": 2, "chunk_index": 0},
                ),
                0.2,
            ),
            (
                Document(
                    page_content="missing scope metadata",
                    metadata={"document_id": 3, "chunk_index": 0},
                ),
                0.0,
            ),
            (
                Document(
                    page_content="string scope metadata",
                    metadata={"knowledge_base_id": "11", "document_id": 4, "chunk_index": 0},
                ),
                0.0,
            ),
        ]


@pytest.mark.asyncio
async def test_retrieval_filters_chunks_outside_the_requested_knowledge_base_scope():
    """A cross-collection vector-store defect must not leak another KB's chunk."""
    service = RetrievalService(_CrossScopeVectorStore(), similarity_threshold=0.0)

    results = await service.retrieve([11, 22], "deployment steps", top_k=3)

    assert [document.page_content for document, _ in results] == ["from kb 11", "from kb 22"]


def test_citation_validation_requires_a_citation_when_context_was_selected():
    """A grounded answer without a source tag must not be marked as validated."""
    result = CitationService().validate(
        "The deployment requires approval.",
        [{"document_id": 8, "chunk_index": 1, "content": "approval required"}],
    )

    assert result["valid"] is False
    assert result["missing_citation_ids"] == []
    assert result["referenced_citation_ids"] == []


@pytest.mark.asyncio
async def test_rag_query_retries_a_transient_dashscope_timeout():
    """Bypassing the shared retry helper would make one timeout fail a grounded query."""
    from app.langchain_integration.rag_chain import RAGManager

    class _SingleKbVectorStore:
        async def similarity_search_with_score(self, knowledge_base_id, query, k):
            return [
                (
                    Document(
                        page_content="restart the deployment",
                        metadata={
                            "knowledge_base_id": 1,
                            "document_id": 7,
                            "chunk_index": 0,
                            "source": "runbook.md",
                        },
                    ),
                    0.1,
                )
            ]

    class _RetryingLLM:
        def __init__(self):
            self.llm = self
            self.attempts = 0

        async def ainvoke(self, prompt):
            self.attempts += 1
            if self.attempts == 1:
                raise TimeoutError("DashScope timeout")
            return "Restart it [citation:7:0]"

    llm = _RetryingLLM()
    manager = RAGManager(vector_store_manager=_SingleKbVectorStore(), llm=llm)

    response = await manager.query([1], "How do I restart it?", top_k=1)

    assert response.answer == "Restart it [citation:7:0]"
    assert llm.attempts == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("transient_error", [TimeoutError, ConnectionError])
async def test_rag_stream_retries_transient_dashscope_failures_before_emitting_error(
    transient_error,
):
    """A first-attempt connection failure must not become a terminal SSE error."""
    from app.langchain_integration.rag_chain import RAGManager

    class _SingleKbVectorStore:
        async def similarity_search_with_score(self, knowledge_base_id, query, k):
            return [
                (
                    Document(
                        page_content="restart the deployment",
                        metadata={
                            "knowledge_base_id": 1,
                            "document_id": 7,
                            "chunk_index": 0,
                            "source": "runbook.md",
                        },
                    ),
                    0.1,
                )
            ]

    class _RetryingStreamLLM:
        def __init__(self):
            self.llm = self
            self.attempts = 0

        async def astream(self, prompt):
            self.attempts += 1
            if self.attempts == 1:
                raise transient_error("DashScope transient failure")
            yield "Restart it "
            yield "[citation:7:0]"

    llm = _RetryingStreamLLM()
    manager = RAGManager(vector_store_manager=_SingleKbVectorStore(), llm=llm)

    events = [event async for event in manager.stream_query([1], "How do I restart it?", 1)]

    assert [event["type"] for event in events] == ["sources", "token", "token", "done"]
    assert llm.attempts == 2


@pytest.mark.asyncio
async def test_rag_stream_bounds_retries_before_emitting_terminal_error():
    """A permanently unavailable DashScope stream must not retry indefinitely."""
    from app.langchain_integration.rag_chain import RAGManager

    class _SingleKbVectorStore:
        async def similarity_search_with_score(self, knowledge_base_id, query, k):
            return [
                (
                    Document(
                        page_content="restart the deployment",
                        metadata={
                            "knowledge_base_id": 1,
                            "document_id": 7,
                            "chunk_index": 0,
                            "source": "runbook.md",
                        },
                    ),
                    0.1,
                )
            ]

    class _UnavailableStreamLLM:
        def __init__(self):
            self.llm = self
            self.attempts = 0

        async def astream(self, prompt):
            self.attempts += 1
            raise TimeoutError("DashScope unavailable")
            yield "unreachable"

    llm = _UnavailableStreamLLM()
    manager = RAGManager(vector_store_manager=_SingleKbVectorStore(), llm=llm)

    events = [event async for event in manager.stream_query([1], "How do I restart it?", 1)]

    assert [event["type"] for event in events] == ["sources", "error"]
    assert llm.attempts == 3
