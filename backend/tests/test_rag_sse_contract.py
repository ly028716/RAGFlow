"""SSE boundary contracts for the local RAG endpoint."""

import json

from app.models.knowledge_base import KnowledgeBase


class _AllowedQuota:
    def check_quota(self, user_id, tokens_required):
        return True

    def consume_quota(self, user_id, tokens_used):
        return None


def _read_sse_events(client, headers, payload):
    events = []
    with client.stream(
        "POST", "/api/v1/rag/query/stream", headers=headers, json=payload
    ) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line and line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


def test_rag_stream_emits_sources_tokens_then_done_with_timing_metrics(
    client, auth_headers, db, test_user, monkeypatch
):
    """Removing timings or changing event order breaks the frontend stream consumer."""
    import app.api.v1.rag as rag_api

    knowledge_base = KnowledgeBase(user_id=test_user.id, name="stream contract")
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    class _ContractManager:
        async def stream_query(self, **kwargs):
            yield {
                "type": "sources",
                "sources": [
                    {
                        "content": "policy",
                        "document_name": "guide.md",
                        "similarity_score": 0.9,
                    }
                ],
                "retrieval_time_ms": 12.5,
            }
            yield {"type": "token", "content": "grounded "}
            yield {"type": "token", "content": "answer"}
            yield {
                "type": "done",
                "content": "grounded answer",
                "tokens_used": 7,
                "retrieval_time_ms": 12.5,
                "generation_time_ms": 34.5,
            }

    monkeypatch.setattr(rag_api, "get_rag_manager", lambda: _ContractManager())
    monkeypatch.setattr(rag_api, "QuotaService", lambda db: _AllowedQuota())

    events = _read_sse_events(
        client,
        auth_headers,
        {"knowledge_base_ids": [knowledge_base.id], "question": "What is the policy?"},
    )

    assert [event["type"] for event in events] == ["sources", "token", "token", "done"]
    assert events[0]["retrieval_time_ms"] == 12.5
    assert events[-1]["retrieval_time_ms"] == 12.5
    assert events[-1]["generation_time_ms"] == 34.5


def test_rag_stream_stops_after_the_first_error_event(
    client, auth_headers, db, test_user, monkeypatch
):
    """Continuing after an error can make clients display a failed answer as complete."""
    import app.api.v1.rag as rag_api

    knowledge_base = KnowledgeBase(user_id=test_user.id, name="stream error contract")
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    class _InvalidUpstreamManager:
        async def stream_query(self, **kwargs):
            yield {"type": "error", "error": "upstream failure"}
            yield {"type": "token", "content": "must not reach client"}
            yield {"type": "done", "content": "must not reach client", "tokens_used": 1}

    monkeypatch.setattr(rag_api, "get_rag_manager", lambda: _InvalidUpstreamManager())
    monkeypatch.setattr(rag_api, "QuotaService", lambda db: _AllowedQuota())

    events = _read_sse_events(
        client,
        auth_headers,
        {"knowledge_base_ids": [knowledge_base.id], "question": "What is the policy?"},
    )

    assert [event["type"] for event in events] == ["error"]
