"""Regression tests for document-processing task imports."""


def test_document_task_module_imports_without_a_circular_dependency() -> None:
    """Document processing remains importable during application startup."""
    from app.tasks.document_tasks import process_document_task

    assert callable(process_document_task)
