import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "012_remove_openclaw_tables.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_012", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_upgrade_drops_existing_openclaw_tables_without_requiring_index_names(monkeypatch):
    migration = _load_migration_module()
    dropped_tables = []

    class Inspector:
        def has_table(self, table_name):
            return table_name == "openclaw_tool_calls"

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.sa, "inspect", lambda bind: Inspector())
    monkeypatch.setattr(migration.op, "drop_table", dropped_tables.append)

    migration.upgrade()

    assert dropped_tables == ["openclaw_tool_calls"]
