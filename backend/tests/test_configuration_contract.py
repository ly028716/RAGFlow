"""Contracts for the constrained DashScope configuration and evaluation kit."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import TongyiSettings


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent


def _read_env_template() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in (BACKEND_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def test_example_environment_declares_the_dashscope_rag_contract() -> None:
    """The checked-in template must document the only supported online providers."""
    values = _read_env_template()

    assert values["LLM_PROVIDER"] == "dashscope"
    assert values["LLM_MODEL"] == "qwen-plus"
    assert values["EMBEDDING_PROVIDER"] == "dashscope"
    assert values["EMBEDDING_MODEL"] == "text-embedding-v3"


def test_tongyi_settings_reads_the_dashscope_provider_contract(monkeypatch) -> None:
    """Provider/model values are loaded from the runtime environment, not docs alone."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LLM_PROVIDER", "dashscope")
    monkeypatch.setenv("LLM_MODEL", "qwen-plus")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dashscope")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-v3")

    config = TongyiSettings(_env_file=None)

    assert config.llm_provider == "dashscope"
    assert config.tongyi_model_name == "qwen-plus"
    assert config.embedding_provider == "dashscope"
    assert config.embedding_model == "text-embedding-v3"


def test_tongyi_settings_rejects_non_dashscope_provider(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "another-provider")

    with pytest.raises(ValidationError, match="dashscope"):
        TongyiSettings(_env_file=None)


def test_evaluation_dataset_references_the_versioned_demo_corpus() -> None:
    """Every expected document ID resolves to a checked-in corpus source and mapping."""
    corpus_root = REPOSITORY_ROOT / "docs" / "evaluation-corpus" / "rag-agent-demo"
    manifest = json.loads((corpus_root / "manifest.json").read_text(encoding="utf-8"))
    dataset = [
        json.loads(line)
        for line in (REPOSITORY_ROOT / "docs" / "rag-evaluation-dataset.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    documents = {item["logical_document_id"]: item for item in manifest["documents"]}

    assert manifest["corpus_id"] == "rag-agent-demo-v1"
    assert len(dataset) == 24
    for record in dataset:
        for document_id in record["expected_document_ids"]:
            document = documents[document_id]
            assert (corpus_root / document["corpus_path"]).is_file()
            assert document["expected_source_identifier"] == (
                f"rag-agent-demo-v1/{document_id}"
            )


def test_frontend_and_openapi_examples_use_the_dashscope_model_contract() -> None:
    """User-facing defaults and generated OpenAPI examples match backend defaults."""
    from app.schemas.system import SystemConfigResponse

    settings_source = (
        REPOSITORY_ROOT / "frontend" / "src" / "views" / "settings" / "SettingsView.vue"
    ).read_text(encoding="utf-8")
    schema_example = SystemConfigResponse.model_config["json_schema_extra"]["example"]

    assert "qwen-plus" in settings_source
    assert "text-embedding-v3" in settings_source
    assert "qwen-turbo" not in settings_source
    assert "text-embedding-v1" not in settings_source
    assert schema_example["tongyi"]["llm_provider"] == "dashscope"
    assert schema_example["tongyi"]["model_name"] == "qwen-plus"
    assert schema_example["tongyi"]["embedding_provider"] == "dashscope"
    assert schema_example["tongyi"]["embedding_model"] == "text-embedding-v3"
