from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def _load_script_directory() -> ScriptDirectory:
    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "app" / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "app" / "alembic"))
    return ScriptDirectory.from_config(config)


def test_alembic_has_single_head() -> None:
    script = _load_script_directory()
    assert script.get_heads() == ["20260416_1100"]


def test_alembic_revision_ids_are_unique() -> None:
    script = _load_script_directory()
    revisions = [revision.revision for revision in script.walk_revisions()]
    assert len(revisions) == len(set(revisions))
