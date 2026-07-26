"""Regression tests for removing the obsolete OpenClaw schema."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[2]
MIGRATION_PATH = BACKEND_DIR / "migrations" / "versions" / "012_remove_openclaw_tables.py"


class OperationsRecorder:
    """Captures the Alembic operations issued by a migration."""

    def __init__(self) -> None:
        self.dropped_tables: list[str] = []
        self.dropped_indexes: list[tuple[str, str | None]] = []
        self.created_tables: list[tuple[object, ...]] = []
        self.created_indexes: list[tuple[str, str, tuple[str, ...], bool]] = []

    def drop_table(self, table_name: str) -> None:
        self.dropped_tables.append(table_name)

    def drop_index(self, index_name: str, table_name: str | None = None) -> None:
        self.dropped_indexes.append((index_name, table_name))

    def create_table(self, table_name: str, *columns: object, **_: object) -> None:
        self.created_tables.append((table_name, *columns))

    def create_index(
        self,
        index_name: str,
        table_name: str,
        columns: list[str],
        *,
        unique: bool = False,
    ) -> None:
        self.created_indexes.append((index_name, table_name, tuple(columns), unique))


def load_migration() -> ModuleType:
    """Load migration 012 directly so its Alembic operations are observable."""
    if not MIGRATION_PATH.is_file():
        pytest.fail("migration 012_remove_openclaw_tables.py must exist")

    spec = importlib.util.spec_from_file_location("remove_openclaw_tables", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def column_names(table: tuple[object, ...]) -> list[str]:
    """Return the column names captured from an ``op.create_table`` call."""
    return [item.name for item in table[1:] if item.__class__.__name__ == "Column"]


def test_upgrade_removes_only_openclaw_tables_and_their_indexes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Catches a migration that drops Web Scraper tables or leaves OpenClaw indexes behind."""
    migration = load_migration()
    operations = OperationsRecorder()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()

    assert operations.dropped_indexes == [
        ("ix_openclaw_tool_calls_created_at", "openclaw_tool_calls"),
        ("ix_openclaw_tool_calls_status", "openclaw_tool_calls"),
        ("ix_openclaw_tool_calls_user_id", "openclaw_tool_calls"),
        ("ix_openclaw_tool_calls_agent_id", "openclaw_tool_calls"),
        ("ix_openclaw_tool_calls_tool_id", "openclaw_tool_calls"),
        ("ix_openclaw_tool_calls_id", "openclaw_tool_calls"),
        ("ix_openclaw_tools_status", "openclaw_tools"),
        ("ix_openclaw_tools_name", "openclaw_tools"),
        ("ix_openclaw_tools_id", "openclaw_tools"),
    ]
    assert operations.dropped_tables == ["openclaw_tool_calls", "openclaw_tools"]
    assert "web_scraper_tasks" not in operations.dropped_tables
    assert "web_scraper_logs" not in operations.dropped_tables


def test_downgrade_restores_the_openclaw_schema_from_migration_009(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches a downgrade that cannot restore the OpenClaw tables removed by upgrade."""
    migration = load_migration()
    operations = OperationsRecorder()
    monkeypatch.setattr(migration, "op", operations)

    migration.downgrade()

    assert [table[0] for table in operations.created_tables] == [
        "openclaw_tools",
        "openclaw_tool_calls",
    ]
    assert column_names(operations.created_tables[0]) == [
        "id",
        "name",
        "display_name",
        "description",
        "endpoint_url",
        "method",
        "auth_type",
        "auth_config",
        "parameters_schema",
        "response_schema",
        "status",
        "is_builtin",
        "created_by",
        "created_at",
        "updated_at",
    ]
    assert column_names(operations.created_tables[1]) == [
        "id",
        "tool_id",
        "agent_id",
        "user_id",
        "request_params",
        "response_data",
        "status",
        "error_message",
        "execution_time",
        "created_at",
    ]
    assert operations.created_indexes == [
        ("ix_openclaw_tools_id", "openclaw_tools", ("id",), False),
        ("ix_openclaw_tools_name", "openclaw_tools", ("name",), True),
        ("ix_openclaw_tools_status", "openclaw_tools", ("status",), False),
        ("ix_openclaw_tool_calls_id", "openclaw_tool_calls", ("id",), False),
        ("ix_openclaw_tool_calls_tool_id", "openclaw_tool_calls", ("tool_id",), False),
        ("ix_openclaw_tool_calls_agent_id", "openclaw_tool_calls", ("agent_id",), False),
        ("ix_openclaw_tool_calls_user_id", "openclaw_tool_calls", ("user_id",), False),
        ("ix_openclaw_tool_calls_status", "openclaw_tool_calls", ("status",), False),
        ("ix_openclaw_tool_calls_created_at", "openclaw_tool_calls", ("created_at",), False),
    ]


def test_v1_api_router_does_not_expose_web_scraper_routes() -> None:
    """Catches accidentally re-registering the removed Web Scraper router."""
    from app.api.v1 import api_router

    assert all("/web-scraper" not in route.path for route in api_router.routes)
