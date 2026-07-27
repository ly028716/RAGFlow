"""Permission boundaries for multi-knowledge-base RAG requests."""

from app.models.knowledge_base import KnowledgeBase


def test_rag_query_rejects_the_entire_multi_kb_request_when_one_kb_is_private(
    client, auth_headers, db, test_user, other_user, monkeypatch
):
    """A private KB in a mixed request must never reach retrieval or the LLM."""
    import app.api.v1.rag as rag_api

    owned = KnowledgeBase(user_id=test_user.id, name="owned")
    private = KnowledgeBase(user_id=other_user.id, name="private")
    db.add_all([owned, private])
    db.commit()
    db.refresh(owned)
    db.refresh(private)

    class _NoCallRagManager:
        def __init__(self):
            self.called = False

        async def query(self, **kwargs):
            self.called = True
            raise AssertionError("private knowledge base reached retrieval")

    manager = _NoCallRagManager()
    monkeypatch.setattr(rag_api, "get_rag_manager", lambda: manager)

    response = client.post(
        "/api/v1/rag/query",
        headers=auth_headers,
        json={
            "knowledge_base_ids": [owned.id, private.id],
            "question": "summarize both",
        },
    )

    assert response.status_code == 404
    assert manager.called is False
