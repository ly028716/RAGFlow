import json


def test_rag_query_works_with_rate_limit_decorator(
    client, auth_headers, db, test_user, monkeypatch
):
    from app.langchain_integration.rag_chain import DocumentChunk, RAGResponse
    from app.models.knowledge_base import KnowledgeBase
    from app.models.knowledge_base_permission import KnowledgeBasePermission, PermissionType

    kb = KnowledgeBase(
        user_id=test_user.id,
        name="kb",
        description="kb",
        category="",
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)

    perm = KnowledgeBasePermission(
        knowledge_base_id=kb.id,
        user_id=test_user.id,
        permission_type=PermissionType.OWNER.value,
        is_public=False,
    )
    db.add(perm)
    db.commit()

    class _StubManager:
        async def query(self, knowledge_base_ids, question, top_k=None, conversation_id=None):
            return RAGResponse(
                answer="ok",
                sources=[DocumentChunk(content="c", document_name="d", similarity_score=0.9)],
                tokens_used=3,
                retrieval_time_ms=12.5,
                generation_time_ms=34.5,
            )

    import app.api.v1.rag as rag_api

    monkeypatch.setattr(rag_api, "get_rag_manager", lambda: _StubManager(), raising=True)

    payload = {"knowledge_base_ids": [kb.id], "question": "hi", "top_k": 1}
    resp = client.post("/api/v1/rag/query", headers=auth_headers, json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "ok"
    assert body["tokens_used"] == 3
    assert body["sources"][0]["document_name"] == "d"
    assert body["retrieval_time_ms"] == 12.5
    assert body["generation_time_ms"] == 34.5


def test_rag_query_stream_works_with_rate_limit_decorator(
    client, auth_headers, db, test_user, monkeypatch
):
    from app.models.knowledge_base import KnowledgeBase
    from app.models.knowledge_base_permission import KnowledgeBasePermission, PermissionType

    kb = KnowledgeBase(
        user_id=test_user.id,
        name="kb",
        description="kb",
        category="",
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)

    perm = KnowledgeBasePermission(
        knowledge_base_id=kb.id,
        user_id=test_user.id,
        permission_type=PermissionType.OWNER.value,
        is_public=False,
    )
    db.add(perm)
    db.commit()

    class _StubManager:
        async def stream_query(self, knowledge_base_ids, question, top_k=None, conversation_id=None):
            yield {"type": "sources", "sources": [], "retrieval_time_ms": 12.5}
            yield {"type": "token", "content": "ok"}
            yield {
                "type": "done",
                "content": "ok",
                "tokens_used": 2,
                "retrieval_time_ms": 12.5,
                "generation_time_ms": 34.5,
            }

    import app.api.v1.rag as rag_api

    monkeypatch.setattr(rag_api, "get_rag_manager", lambda: _StubManager(), raising=True)

    payload = {"knowledge_base_ids": [kb.id], "question": "hi", "top_k": 1}

    events = []
    with client.stream(
        "POST", "/api/v1/rag/query/stream", headers=auth_headers, json=payload
    ) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith("data: "):
                data = line[6:].strip()
                events.append(json.loads(data))
                if events[-1].get("type") == "done":
                    break

    assert any(e.get("type") == "token" for e in events)
    assert any(e.get("type") == "done" for e in events)
    sources_event = next(e for e in events if e.get("type") == "sources")
    done_event = next(e for e in events if e.get("type") == "done")
    assert sources_event["retrieval_time_ms"] == 12.5
    assert done_event["retrieval_time_ms"] == 12.5
    assert done_event["generation_time_ms"] == 34.5

