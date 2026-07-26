"""Static regression coverage for the retired Web Scraper runtime."""

from __future__ import annotations

from pathlib import Path


WORKTREE_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_PATHS = (
    "backend/app/core/scheduler.py",
    "backend/app/core/url_validator.py",
    "backend/app/schemas/web_scraper_validators.py",
    "frontend/src/types/webScraper.ts",
)
DEPLOYMENT_CONFIGS = (
    "backend/.env.example",
    "backend/docker-compose.yml",
    "backend/docker-compose.prod.yml",
)
BUILD_CONFIGS = (
    "backend/Dockerfile",
    "backend/requirements.txt",
)
PRESERVED_MIGRATIONS = (
    "backend/migrations/versions/010_add_web_scraper_tables.py",
    "backend/migrations/versions/011_add_web_scraper_indexes.py",
)


def scraper_references(root: Path) -> list[Path]:
    """Return runtime source files which still contain a Scraper reference."""
    matches: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".ts", ".vue"}:
            continue
        if "scraper" in path.read_text(encoding="utf-8").lower():
            matches.append(path.relative_to(WORKTREE_ROOT))
    return matches


def test_web_scraper_runtime_modules_and_references_are_removed() -> None:
    """Catches restoring the retired scheduler, validation, or frontend runtime."""
    assert [path for path in RUNTIME_PATHS if (WORKTREE_ROOT / path).exists()] == []
    assert scraper_references(WORKTREE_ROOT / "backend" / "app") == []
    assert scraper_references(WORKTREE_ROOT / "frontend" / "src") == []


def test_deployment_configuration_has_no_scraper_settings() -> None:
    """Catches exposing retired Scraper or Playwright deployment settings."""
    for relative_path in DEPLOYMENT_CONFIGS:
        content = (WORKTREE_ROOT / relative_path).read_text(encoding="utf-8")
        assert "SCRAPER_" not in content
        assert "PLAYWRIGHT_BROWSERS_PATH" not in content


def test_build_configuration_has_no_web_scraper_dependencies() -> None:
    """Catches reintroducing browser automation dependencies for the removed runtime."""
    for relative_path in BUILD_CONFIGS:
        content = (WORKTREE_ROOT / relative_path).read_text(encoding="utf-8").lower()
        assert "playwright" not in content
        assert "beautifulsoup4" not in content
        assert "lxml==" not in content
        assert "html2text" not in content


def test_web_scraper_schema_migrations_remain_in_history() -> None:
    """Catches accidentally deleting the migrations that preserve existing Scraper data."""
    assert all((WORKTREE_ROOT / path).is_file() for path in PRESERVED_MIGRATIONS)
