"""Unit contracts for the API-first RAG evaluation runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_runner_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_rag_evaluation.py"
    spec = importlib.util.spec_from_file_location("run_rag_evaluation", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_score_retrieval_calculates_recall_hit_rate_and_mrr():
    runner = _load_runner_module()

    score = runner.score_retrieval(
        expected_document_ids=[101, 102],
        retrieved_document_ids=[102, 999, 101],
    )

    assert score == {
        "recall_at_k": 1.0,
        "hit": True,
        "reciprocal_rank": 1.0,
        "matched_document_ids": [101, 102],
    }


def test_score_retrieval_excludes_unanswerable_case():
    runner = _load_runner_module()

    score = runner.score_retrieval(expected_document_ids=[], retrieved_document_ids=[101])

    assert score == {
        "recall_at_k": None,
        "hit": None,
        "reciprocal_rank": None,
        "matched_document_ids": [],
    }


def test_extract_agent_result_reads_retrieval_citation_and_timings():
    runner = _load_runner_module()
    events = [
        {
            "type": "step",
            "data": {
                "step_number": 2,
                "data": {
                    "raw_chunks": [
                        {"document_id": 101, "similarity_score": 0.95},
                        {"document_id": 102, "similarity_score": 0.87},
                    ],
                    "retrieval_time_ms": 12.5,
                },
            },
        },
        {
            "type": "result",
            "data": {
                "result": "grounded answer [citation:101:0]",
                "metrics": {
                    "retrieval_time_ms": 12.5,
                    "generation_time_ms": 31.0,
                    "total_time_ms": 50.0,
                },
                "steps": [
                    {
                        "step_number": 4,
                        "data": {"citation_validation": {"valid": True}},
                    }
                ],
            },
        },
    ]

    result = runner.extract_agent_result(events, first_token_latency_ms=44.0)

    assert result["retrieved_document_ids"] == [101, 102]
    assert result["citation_valid"] is True
    assert result["retrieval_time_ms"] == 12.5
    assert result["generation_time_ms"] == 31.0
    assert result["first_token_latency_ms"] == 44.0


def test_refusal_requires_configured_phrase_and_no_citation():
    runner = _load_runner_module()

    assert runner.is_refusal(
        "当前所选知识库中未找到足够相关的信息，无法基于知识库回答该问题。",
        ["未找到足够相关的信息", "无法基于知识库回答"],
    )
    assert not runner.is_refusal(
        "当前所选知识库中未找到足够相关的信息[citation:101:0]",
        ["未找到足够相关的信息"],
    )


def test_markdown_report_leaves_unavailable_metrics_blank():
    runner = _load_runner_module()
    report = runner.markdown_report(
        {
            "run_at_utc": "2026-08-31T00:00:00+00:00", "git_commit": "abc",
            "corpus_id": "vehicle-agent-demo-v1", "mode": "agent",
            "llm_model": "qwen-plus", "embedding_model": "text-embedding-v3",
            "top_k": 5, "similarity_threshold": 0.7, "chunk_size": 1000, "chunk_overlap": 200,
        },
        {
            "recall_at_k": None, "hit_rate": None, "mrr": None,
            "citation_validity_rate": None, "average_retrieval_time_ms": None,
            "average_generation_time_ms": None, "average_first_token_latency_ms": None,
            "refusal_rate": None,
        },
        [],
    )

    assert "| — | — | — |" in report
    assert "Faithfulness" in report and "Answer Relevancy" in report


def test_importer_loads_manifest_from_requested_corpus_root(tmp_path):
    path = Path(__file__).resolve().parents[1] / "scripts" / "import_rag_evaluation_corpus.py"
    spec = importlib.util.spec_from_file_location("import_rag_evaluation_corpus", path)
    assert spec and spec.loader
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    manifest = {"corpus_id": "test-corpus", "documents": []}
    (tmp_path / "manifest.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")

    assert importer.load_manifest(tmp_path) == manifest
