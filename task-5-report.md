# Task 5 report — vector cleanup and RAG verification

## Delivered

- Moved knowledge-base vector collection cleanup into `KnowledgeBaseService.delete`, after ownership validation and before relational deletion. File cleanup now lives in the same service layer, and the legacy `RAGService` facade delegates without bypassing authorization or repeating destructive work.
- Kept deletion resilient: Chroma cleanup failures are logged, while the owner can still remove the relational knowledge base and its files.
- Added defensive retrieval filtering so a malformed or cross-scope vector-store result cannot expose a chunk outside the requested knowledge-base IDs.
- Made non-stream RAG generation use the shared retrying DashScope invocation helper.
- Made the RAG SSE adapter stop immediately after forwarding an error event.
- Added focused contracts for vector cleanup order, deletion resilience, multi-KB scope isolation, private-KB permission enforcement, citation completeness, DashScope timeout retry, and SSE ordering/timing/error termination.

## Verification

- Passed: `python -m py_compile` for all modified production modules and focused test modules.
- Passed: `git diff --check`.
- Attempted before and after implementation: `python -m pytest tests/services/test_knowledge_base_vector_cleanup.py tests/test_rag_sse_contract.py tests/test_rag_resilience.py tests/test_rag_permissions.py -q`.
  Collection is blocked before any test executes because the available Python environment lacks `apscheduler`, imported by `backend/app/main.py` through `tests/conftest.py`.

## TDD note

The focused contracts were written before the production changes. Runtime red/green execution could not reach collection due to the pre-existing missing dependency; syntax compilation and static diff checks succeeded.
