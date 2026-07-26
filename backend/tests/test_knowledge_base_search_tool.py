import json

import pytest
from langchain_core.documents import Document

from app.langchain_integration.tools import KnowledgeBaseSearchTool


class FakeRetrievalService:
    def __init__(self, manager):
        self.manager = manager

    async def retrieve(self, knowledge_base_ids, query, top_k):
        assert knowledge_base_ids == [7]
        assert query == "部署流程"
        assert top_k == 2
        return [
            (
                Document(
                    page_content="部署步骤...",
                    metadata={
                        "knowledge_base_id": 7,
                        "document_id": 42,
                        "chunk_index": 3,
                        "source": "runbook.md",
                    },
                ),
                0.91,
            )
        ]


@pytest.mark.asyncio
async def test_knowledge_base_search_returns_citation_ready_results(monkeypatch):
    monkeypatch.setattr(
        "app.langchain_integration.tools.knowledge_base_search_tool.get_vector_store_manager",
        lambda: object(),
    )
    monkeypatch.setattr(
        "app.langchain_integration.tools.knowledge_base_search_tool.RetrievalService",
        FakeRetrievalService,
    )

    result = await KnowledgeBaseSearchTool(allowed_knowledge_base_ids=[7]).ainvoke(
        {"query": "部署流程", "knowledge_base_ids": [7], "top_k": 2}
    )
    payload = json.loads(result)

    assert payload["count"] == 1
    assert payload["results"][0] == {
        "knowledge_base_id": 7,
        "document_id": 42,
        "chunk_index": 3,
        "content": "部署步骤...",
        "similarity": 0.91,
        "source": "runbook.md",
    }


@pytest.mark.asyncio
async def test_knowledge_base_search_returns_empty_results_without_query(monkeypatch):
    monkeypatch.setattr(
        "app.langchain_integration.tools.knowledge_base_search_tool.get_vector_store_manager",
        lambda: object(),
    )
    monkeypatch.setattr(
        "app.langchain_integration.tools.knowledge_base_search_tool.RetrievalService",
        FakeRetrievalService,
    )

    with pytest.raises(Exception):
        await KnowledgeBaseSearchTool(allowed_knowledge_base_ids=[7]).ainvoke(
            {"query": "", "knowledge_base_ids": [7], "top_k": 2}
        )
