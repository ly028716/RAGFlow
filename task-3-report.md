# Task 3 report — constrained four-stage RAG Agent

## Implemented

- Added deterministic query rewriting, context selection and citation validation services.
- Added JSON-emitting `query_rewriter`, `context_selector` and `citation_validator` tools.
- Replaced ReAct/custom-tool execution with the fixed workflow:
  `query_rewriter` → `knowledge_base_search` → `context_selector` → answer plus `citation_validator`.
- Removed `tool_ids` from the task execution request/call chain. The executor exposes only the four constrained RAG tools.
- Persisted JSON-safe structured step data for the original question, rewritten query, KB scope, retrieval parameters, raw and filtered chunks, final context, answer, citation validation, token usage and timing metrics.
- Added service tests and focused Agent workflow tests before implementation.

## Verification

- `python -m py_compile` completed successfully for all modified production files and focused tests.
- Isolated real assertions for the three pure services completed successfully (`PASS`).
- `pytest tests/services/test_query_rewrite_service.py tests/services/test_context_selector_service.py tests/services/test_citation_service.py tests/test_agent_executor.py -v` is blocked before collection: `ModuleNotFoundError: No module named 'apscheduler'` while importing `backend/tests/conftest.py` → `app.main`.

## Limitation

The available system Python also lacks `pymysql`, so importing the project's aggregate `app.services` package cannot be used as an alternative integration harness. No dependencies were installed as part of this task.

## Review follow-up

- Reworked streaming execution so it emits each completed rewrite/retrieval/context stage as soon as it is available, streams LLM answer deltas, then emits citation validation and the final result.
- Streaming persistence now records terminal `COMPLETED`/`FAILED` status, final answer, full steps and completion time; client-facing errors remain sanitized.
- Restored the legacy `execute_task(task, tool_ids, custom_tools, max_iterations, verbose, knowledge_base_ids)` positional contract. Legacy tool ids are ignored and nonempty custom tools are rejected.
- Replaced the direct Tongyi construction with `get_llm()` and `get_streaming_llm()` factories. The final rendered context now includes citation-tag overhead in its character budget.
- Added focused regression coverage for the streaming order, terminal persistence, compatibility and LLM factory behavior. Focused pytest remains blocked by the same missing `apscheduler` dependency; revised files pass `py_compile`.
