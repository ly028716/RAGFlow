"""Persistence regression tests for streaming constrained RAG executions."""

import asyncio

import pytest

from app.models.agent_execution import ExecutionStatus
from app.repositories.agent_repository import AgentExecutionRepository
from app.services.agent.execution_service import TaskExecutionService


class CompletedStreamManager:
    async def stream_execute_task(self, *_args, **_kwargs):
        step = {
            "step_number": 1,
            "thought": "rewrite",
            "action": "query_rewriter",
            "action_input": {"question": "q"},
            "observation": "{}",
            "timestamp": "2026-07-27T00:00:00",
        }
        yield {"type": "step", "data": step}
        yield {
            "type": "result",
            "data": {
                "result": "answer [citation:1:0]",
                "steps": [step],
                "status": "completed",
                "metrics": {"total_time_ms": 12.0},
            },
        }


class FailedStreamManager:
    async def stream_execute_task(self, *_args, **_kwargs):
        yield {"type": "error", "data": {"message": "provider timeout", "steps": []}}


class HangingStreamManager:
    async def stream_execute_task(self, *_args, **_kwargs):
        yield {
            "type": "step",
            "data": {
                "step_number": 1,
                "thought": "rewrite",
                "action": "query_rewriter",
                "action_input": {"question": "q"},
                "observation": "{}",
                "timestamp": "2026-07-27T00:00:00",
            },
        }
        await asyncio.Event().wait()


@pytest.mark.asyncio
async def test_stream_execution_persists_completed_result_and_steps(db, test_user):
    service = TaskExecutionService(db)
    service.agent_manager = CompletedStreamManager()

    events = [event async for event in service.stream_execute(user_id=test_user.id, task="q")]

    execution_id = events[0]["data"]["execution_id"]
    execution = AgentExecutionRepository(db).get_by_id(execution_id)
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.result == "answer [citation:1:0]"
    assert execution.completed_at is not None
    assert execution.steps == events[-1]["data"]["steps"]


@pytest.mark.asyncio
async def test_stream_execution_persists_failed_status_without_leaking_error(db, test_user):
    service = TaskExecutionService(db)
    service.agent_manager = FailedStreamManager()

    events = [event async for event in service.stream_execute(user_id=test_user.id, task="q")]

    execution_id = events[0]["data"]["execution_id"]
    execution = AgentExecutionRepository(db).get_by_id(execution_id)
    assert execution.status == ExecutionStatus.FAILED
    assert execution.completed_at is not None
    assert "provider timeout" in execution.error_message
    assert events[-1]["data"]["message"] == "任务执行失败"


@pytest.mark.asyncio
async def test_stream_execution_marks_cancelled_generator_as_failed(db, test_user):
    service = TaskExecutionService(db)
    service.agent_manager = HangingStreamManager()
    stream = service.stream_execute(user_id=test_user.id, task="q")

    created = await anext(stream)
    await anext(stream)
    await anext(stream)
    await stream.aclose()

    execution = AgentExecutionRepository(db).get_by_id(created["data"]["execution_id"])
    assert execution.status == ExecutionStatus.FAILED
    assert execution.completed_at is not None
    assert "cancelled" in execution.error_message.lower()
