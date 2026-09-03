"""Contract checks for the checked-in, non-confidential vehicle evaluation corpus."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = ROOT / "docs" / "evaluation-corpus" / "vehicle-agent-demo"
DATASET_PATH = ROOT / "docs" / "vehicle-rag-evaluation-dataset.jsonl"


def test_vehicle_dataset_has_24_unique_cases_with_manifest_documents():
    manifest = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    document_ids = {item["logical_document_id"] for item in manifest["documents"]}
    cases = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert manifest["corpus_id"] == "vehicle-agent-demo-v1"
    assert len(manifest["documents"]) == 15
    assert len(cases) == 24
    assert len({case["id"] for case in cases}) == 24
    for case in cases:
        assert case["question"].strip()
        assert case["expected_answer_points"]
        assert set(case["expected_document_ids"]).issubset(document_ids)


def test_vehicle_dataset_has_five_explicit_unanswerable_cases():
    cases = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    unanswerable = [case for case in cases if case["answerability"] == "unanswerable"]

    assert len(unanswerable) == 5
    assert all(not case["expected_document_ids"] for case in unanswerable)
    assert all(case["expected_refusal_patterns"] for case in unanswerable)
