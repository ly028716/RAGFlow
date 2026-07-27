"""Contract tests for the constrained DashScope-only model configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import TongyiSettings


BACKEND_ROOT = Path(__file__).resolve().parents[1]


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
