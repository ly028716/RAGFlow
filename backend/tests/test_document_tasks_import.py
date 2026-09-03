import ast
from pathlib import Path


RAG_SERVICE_DIR = Path(__file__).resolve().parents[1] / "app" / "services" / "rag"


def test_document_services_do_not_import_tasks_at_module_load_time():
    module_paths = [
        RAG_SERVICE_DIR / "document_action_service.py",
        RAG_SERVICE_DIR / "document_upload_service.py",
    ]
    top_level_task_imports = []

    for module_path in module_paths:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        top_level_task_imports.extend(
            statement
            for statement in tree.body
            if isinstance(statement, ast.ImportFrom)
            and statement.module == "app.tasks.document_tasks"
        )

    assert top_level_task_imports == []
