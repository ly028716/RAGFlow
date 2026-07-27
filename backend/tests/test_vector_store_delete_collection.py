"""Vector-collection deletion contracts."""

import sys
from types import SimpleNamespace

from app.core.vector_store import VectorStoreManager


def _manager() -> VectorStoreManager:
    manager = VectorStoreManager.__new__(VectorStoreManager)
    manager.persist_directory = "unused-for-unit-test"
    manager._vector_stores = {}
    return manager


def test_delete_collection_treats_a_missing_chroma_collection_as_already_deleted(
    monkeypatch,
):
    class MissingCollectionClient:
        def delete_collection(self, _collection_name):
            raise ValueError("Collection knowledge_base_7 does not exist")

    monkeypatch.setitem(
        sys.modules,
        "chromadb",
        SimpleNamespace(PersistentClient=lambda path: MissingCollectionClient()),
    )

    assert _manager().delete_collection(7) is True


def test_delete_collection_fails_closed_for_non_missing_chroma_errors(monkeypatch):
    class BrokenClient:
        def delete_collection(self, _collection_name):
            raise RuntimeError("Chroma disk is unavailable")

    monkeypatch.setitem(
        sys.modules,
        "chromadb",
        SimpleNamespace(PersistentClient=lambda path: BrokenClient()),
    )

    assert _manager().delete_collection(7) is False
