from app.services.rag.citation_service import CitationService


def test_validate_rejects_unknown_citation_ids():
    chunks = [{"document_id": 42, "chunk_index": 3, "content": "部署步骤"}]

    result = CitationService().validate(
        "请遵循 [citation:42:99] 完成部署。", chunks
    )

    assert result["valid"] is False
    assert result["missing_citation_ids"] == ["42:99"]


def test_validate_accepts_citations_from_selected_chunks():
    chunks = [{"document_id": 42, "chunk_index": 3, "content": "部署步骤"}]

    result = CitationService().validate(
        "请遵循 [citation:42:3] 完成部署。", chunks
    )

    assert result["valid"] is True
    assert result["missing_citation_ids"] == []
