"""Tests for scripts/workspace/session-index.py."""

import pytest
from test_helpers import load_module


@pytest.fixture
def si(scripts_dir, tmp_path):
    module = load_module("session_index", scripts_dir / "session-index.py")
    module.SESSIONS_DIR = tmp_path / "memory" / "sessions"
    module.STAGING_DIR = tmp_path / "memory" / "staging"
    module.DB_DIR = tmp_path / "memory" / ".index"
    module.DB_PATH = module.DB_DIR / "sessions.db"
    module.SESSIONS_DIR.mkdir(parents=True)
    module.STAGING_DIR.mkdir(parents=True)
    return module


def write_session(si, name, title):
    (si.SESSIONS_DIR / name).write_text(f"# 2026-06-01: {title}\n\nbody about sprockets\n")


class TestRebuild:
    def test_rebuild_makes_sessions_searchable(self, si):
        write_session(si, "2026-06-01-widget.md", "Widget work")
        si.rebuild_index()
        assert si.DB_PATH.is_file()
        hits = si.search_index("sprockets")
        assert len(hits) == 1
        assert hits[0]["title"] == "Widget work"

    def test_failed_rebuild_leaves_existing_index_intact(self, si, monkeypatch):
        write_session(si, "2026-06-01-widget.md", "Widget work")
        si.rebuild_index()

        write_session(si, "2026-06-02-second.md", "Second session")
        monkeypatch.setattr(si, "parse_date_title", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        with pytest.raises(RuntimeError):
            si.rebuild_index()

        # The live index was never touched, so the old content is still
        # searchable and no half-built database is visible.
        hits = si.search_index("sprockets")
        assert len(hits) == 1
        assert hits[0]["title"] == "Widget work"

    def test_stale_tmp_file_does_not_block_rebuild(self, si):
        write_session(si, "2026-06-01-widget.md", "Widget work")
        si.DB_DIR.mkdir(parents=True, exist_ok=True)
        (si.DB_DIR / (si.DB_PATH.name + ".tmp")).write_bytes(b"stale partial rebuild")
        si.rebuild_index()
        assert si.search_index("sprockets")
