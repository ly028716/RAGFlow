"""Constrained RAG Agent workflow tests."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.langchain_integration.agent_executor import AgentManager


class FakeWorkflowTool:
    """Small tool double that returns a JSON observation for one workflow stage."""

    def __init__(self, name, payload):
        self.name = name
        self.description = name
        self.payload = payload

    async def ainvoke(self, _arguments):
        return json.dumps(self.payload)


@pytest.fixture
def agent_manager():
    with patch("app.langchain_integration.agent_executor.Tongyi"):
        return AgentManager()


class TestAgentManager:
    def test_load_builtin_tools_is_limited_to_four_rag_tools(self, agent_manager):
        assert {tool.name for tool in agent_manager.builtin_tools} == {
            "query_rewriter",
            "knowledge_base_search",
            "context_selector",
            "citation_validator",
        }
        assert {tool.name for tool in agent_manager._select_tools()} == {
            "query_rewriter",
            "knowledge_base_search",
            "context_selector",
            "citation_validator",
        }

    @pytest.mark.asyncio
    async def test_execute_task_records_structured_four_stage_trace(self, agent_manager):
        tools = [
            FakeWorkflowTool(
                "query_rewriter",
                {"original_question": "question", "rewritten_query": "rewritten question"},
            ),
            FakeWorkflowTool(
                "knowledge_base_search",
                {
                    "query": "rewritten question",
                    "count": 1,
                    "results": [
                        {
                            "document_id": 7,
                            "chunk_index": 0,
                            "content": "chunk",
                            "similarity": 0.9,
                        }
                    ],
                    "retrieval_time_ms": 4.0,
                },
            ),
            FakeWorkflowTool(
                "context_selector",
                {
                    "selected_chunks": [
                        {
                            "document_id": 7,
                            "chunk_index": 0,
                            "content": "chunk",
                            "similarity": 0.9,
                        }
                    ]
                },
            ),
            FakeWorkflowTool(
                "citation_validator", {"valid": True, "missing_citation_ids": []}
            ),
        ]
        agent_manager._load_builtin_tools = lambda _scope=None: tools
        agent_manager._generate_answer = AsyncMock(
            return_value={
                "answer": "answer [citation:7:0]",
                "tokens_used": 28,
                "generation_time_ms": 8.0,
            }
        )

        result = await agent_manager.execute_task("question", knowledge_base_ids=[1])

        assert result["status"] == "completed"
        assert [step["action"] for step in result["steps"]] == [
            "query_rewriter",
            "knowledge_base_search",
            "context_selector",
            "citation_validator",
        ]
        assert result["steps"][0]["data"]["original_question"] == "question"
        assert result["steps"][1]["data"]["raw_chunks"][0]["document_id"] == 7
        assert result["steps"][2]["data"]["final_context"]
        assert result["steps"][3]["data"]["citation_validation"]["valid"] is True
        assert result["steps"][3]["data"]["tokens_used"] == 28
        assert result["metrics"]["retrieval_time_ms"] == 4.0
        assert result["metrics"]["generation_time_ms"] == 8.0
        assert result["metrics"]["total_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_execute_task_reports_failure_when_no_tools_are_available(self, agent_manager):
        agent_manager._load_builtin_tools = lambda _scope=None: []

        result = await agent_manager.execute_task("test task", knowledge_base_ids=[1])

        assert result["status"] == "failed"
        assert result["steps"] == []

    @pytest.mark.asyncio
    async def test_execute_task_scopes_knowledge_base_search_to_authorized_ids(
        self, agent_manager
    ):
        with patch.object(
            agent_manager,
            "_run_workflow",
            return_value={"status": "completed", "result": "done", "steps": [], "metrics": {}},
        ):
            result = await agent_manager.execute_task("question", knowledge_base_ids=[1])

        search_tool = next(
            tool
            for tool in agent_manager.builtin_tools
            if tool.name == "knowledge_base_search"
        )
        assert result["status"] == "completed"
        assert search_tool.allowed_knowledge_base_ids == [1]

    @pytest.mark.asyncio
    async def test_stream_execute_task_emits_steps_then_result(self, agent_manager):
        async def workflow(*_args, **_kwargs):
            return {
                "status": "completed",
                "result": "done",
                "steps": [{"action": "query_rewriter"}],
                "metrics": {"total_time_ms": 1.0},
            }

        agent_manager._run_workflow = workflow
        events = [event async for event in agent_manager.stream_execute_task("test task")]

        assert events == [
            {"type": "step", "data": {"action": "query_rewriter"}},
            {
                "type": "result",
                "data": {
                    "result": "done",
                    "steps": [{"action": "query_rewriter"}],
                    "status": "completed",
                    "metrics": {"total_time_ms": 1.0},
                },
            },
        ]
