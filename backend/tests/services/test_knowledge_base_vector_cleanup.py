"""Knowledge-base and document deletion resilience contracts."""

import pytest

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.services.rag.document_action_service import DocumentActionService
from app.services.rag.knowledge_base_service import KnowledgeBaseService


class _InMemoryCollections:
    """Small Chroma substitute that also verifies cleanup ordering."""

    def __init__(self, db, collection_ids):
        self.db = db
        self.collection_ids = set(collection_ids)
        self.deleted_ids = []

    def delete_collection(self, knowledge_base_id):
        # Collection cleanup must happen while the relational KB still exists.
        assert self.db.get(KnowledgeBase, knowledge_base_id) is not None
        self.deleted_ids.append(knowledge_base_id)
        self.collection_ids.discard(knowledge_base_id)
        return True


class _FailingVectorCleanup:
    def __init__(self):
        self.deleted_document_ids = []

    def delete_collection(self, knowledge_base_id):
        raise RuntimeError("Chroma is temporarily unavailable")

    async def delete_by_document_id(self, knowledge_base_id, document_id):
        self.deleted_document_ids.append((knowledge_base_id, document_id))
        raise RuntimeError("Chroma is temporarily unavailable")


def test_delete_knowledge_base_removes_its_collection_before_database_record(
    db, test_user, monkeypatch
):
    """Removing the service-layer cleanup would leave an orphaned collection."""
    import app.services.rag.knowledge_base_service as kb_service_module

    service = KnowledgeBaseService(db)
    knowledge_base = service.create(test_user.id, "cleanup target")
    collections = _InMemoryCollections(db, [knowledge_base.id])
    monkeypatch.setattr(
        kb_service_module, "get_vector_store_manager", lambda: collections
    )

    assert service.delete(knowledge_base.id, test_user.id) is True
    assert collections.deleted_ids == [knowledge_base.id]
    assert collections.collection_ids == set()
    assert db.get(KnowledgeBase, knowledge_base.id) is None


def test_delete_knowledge_base_keeps_database_deletion_available_when_vector_cleanup_fails(
    db, test_user, monkeypatch
):
    """An unavailable Chroma instance must not make a KB impossible to delete."""
    import app.services.rag.knowledge_base_service as kb_service_module

    service = KnowledgeBaseService(db)
    knowledge_base = service.create(test_user.id, "resilient cleanup target")
    failing_cleanup = _FailingVectorCleanup()
    monkeypatch.setattr(
        kb_service_module, "get_vector_store_manager", lambda: failing_cleanup
    )

    assert service.delete(knowledge_base.id, test_user.id) is True
    assert db.get(KnowledgeBase, knowledge_base.id) is None


@pytest.mark.asyncio
async def test_document_delete_removes_database_record_when_vector_cleanup_fails(
    db, test_user, tmp_path, monkeypatch
):
    """A transient vector failure must not strand an otherwise deletable document."""
    import app.services.rag.document_action_service as document_action_module

    knowledge_base = KnowledgeBase(user_id=test_user.id, name="document target")
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    document = Document(
        knowledge_base_id=knowledge_base.id,
        filename="runbook.md",
        file_path=str(tmp_path / "already-removed.md"),
        file_size=12,
        file_type="md",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    failing_cleanup = _FailingVectorCleanup()
    monkeypatch.setattr(
        document_action_module,
        "get_vector_store_manager",
        lambda: failing_cleanup,
    )
    service = DocumentActionService(db)

    assert await service.delete(document.id, test_user.id) is True
    assert failing_cleanup.deleted_document_ids == [(knowledge_base.id, document.id)]
    assert db.get(Document, document.id) is None
