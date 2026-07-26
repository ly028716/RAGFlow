from app.services.rag.context_selector_service import ContextSelectorService


def test_select_keeps_highest_scoring_chunks_within_character_budget():
    chunks = [
        {"document_id": 1, "chunk_index": 0, "content": "low", "similarity": 0.2},
        {"document_id": 2, "chunk_index": 1, "content": "highest", "similarity": 0.9},
        {"document_id": 3, "chunk_index": 2, "content": "middle", "similarity": 0.7},
    ]

    selected = ContextSelectorService().select(chunks, max_chars=13)

    assert [chunk["document_id"] for chunk in selected] == [2, 3]
    assert sum(len(chunk["content"]) for chunk in selected) <= 13


def test_select_skips_a_chunk_that_cannot_fit_and_preserves_lower_scored_fit():
    chunks = [
        {"document_id": 1, "content": "too-long-for-budget", "similarity": 0.9},
        {"document_id": 2, "content": "fits", "similarity": 0.8},
    ]

    assert ContextSelectorService().select(chunks, max_chars=5) == [chunks[1]]
