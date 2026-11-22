"""Tests for scripts/workspace/memory-promoter.py."""

import pathlib

import pytest
from test_helpers import load_module


@pytest.fixture
def mp(scripts_dir, tmp_path):
    """Loaded memory-promoter pointed at a throwaway workspace."""
    module = load_module("memory_promoter", scripts_dir / "memory-promoter.py")
    projects = tmp_path / "wiki" / "1 Projects"
    projects.mkdir(parents=True)
    (tmp_path / "memory" / "sessions").mkdir(parents=True)
    module.WORKSPACE = tmp_path
    module.PROJECTS_DIR = projects
    module.SESSIONS_DIR = tmp_path / "memory" / "sessions"
    return module


@pytest.fixture
def projects(tmp_path):
    return tmp_path / "wiki" / "1 Projects"


class TestDirSlug:
    def test_absolute_path_rejected(self, mp):
        assert mp.dir_slug("/var/new-directory") == ""

    def test_traversal_rejected(self, mp):
        assert mp.dir_slug("../../../new-directory") == ""

    def test_separators_rejected(self, mp):
        assert mp.dir_slug("a/b") == ""
        assert mp.dir_slug("a\\b") == ""
        assert mp.dir_slug("a/../b") == ""

    def test_punctuation_only_topic_yields_empty(self, mp):
        assert mp.dir_slug("///...") == ""

    def test_slug_capped_at_six_words(self, mp):
        assert mp.dir_slug("one two three four five six seven") == "one-two-three-four-five-six"


class TestPromoteContainment:
    """Topics must never escape the projects directory."""

    def test_promotes_into_projects_directory(self, mp, projects):
        created = mp.promote_candidates({"good topic": (3, "Good Topic")})
        note = projects / "good-topic" / "00 Top Note.md"
        assert note in created
        assert "status: active" in note.read_text()
        assert "Referenced 3 times" in note.read_text()

    def test_absolute_topic_rejected(self, mp, projects, tmp_path):
        created = mp.promote_candidates({"/moraine-absolute-escape": (3, "/moraine-absolute-escape")})
        assert created == []
        assert list(tmp_path.rglob("00 Top Note.md")) == []

    def test_traversal_topic_rejected(self, mp, projects, tmp_path):
        outside = tmp_path.parent / "moraine-promoter-traversal-escape"
        created = mp.promote_candidates({"../../../moraine-promoter-traversal-escape": (3, "escape")})
        assert created == []
        assert not outside.exists()
        assert list(projects.iterdir()) == []

    def test_separator_topic_rejected(self, mp, projects):
        created = mp.promote_candidates({"wiki/../../evil plan": (3, "escape")})
        assert created == []
        assert list(projects.iterdir()) == []

    def test_punctuation_only_topic_skipped(self, mp, projects):
        created = mp.promote_candidates({"///...": (3, "///...")})
        assert created == []
        assert list(projects.iterdir()) == []

    def test_symlinked_target_rejected(self, mp, projects, tmp_path):
        # A pre-existing symlink whose name matches a topic slug must not be
        # written through. already_promoted is bypassed to reach the guard.
        outside = tmp_path / "outside-target"
        outside.mkdir()
        (projects / "escape-hatch").symlink_to(outside)
        mp.already_promoted = lambda norm: False
        created = mp.promote_candidates({"escape hatch": (3, "escape hatch")})
        assert created == []
        assert not (outside / "00 Top Note.md").exists()

    def test_existing_note_not_overwritten(self, mp, projects):
        note = projects / "foo-bar" / "00 Top Note.md"
        note.parent.mkdir()
        note.write_text("keep me")
        mp.already_promoted = lambda norm: False
        created = mp.promote_candidates({"foo bar": (3, "foo bar")})
        assert created == []
        assert note.read_text() == "keep me"

    def test_write_failure_leaves_no_partial_directory(self, mp, projects, monkeypatch):
        def failing_open(self, *args, **kwargs):
            raise OSError("simulated write failure")

        monkeypatch.setattr(pathlib.Path, "open", failing_open)
        created = mp.promote_candidates({"foo bar": (3, "foo bar")})
        assert created == []
        assert not (projects / "foo-bar").exists()

    def test_repeated_headings_promote_once(self, mp, projects, tmp_path):
        staging = tmp_path / "memory" / "staging"
        staging.mkdir(parents=True)
        mp.STAGING_DIR = staging
        for day in ("2026-06-01", "2026-06-02", "2026-06-03"):
            (staging / f"{day}.md").write_text(f"## Shared Topic\nnote {day}\n")
        assert mp.scan_staging() == {"shared topic": 3}
        enriched = mp.find_original_forms({"shared topic": 3})
        created = mp.promote_candidates(enriched)
        assert len(created) == 1
        assert (projects / "shared-topic" / "00 Top Note.md").is_file()
