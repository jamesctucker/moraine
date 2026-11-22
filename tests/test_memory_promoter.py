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


class TestPromotedStructures:
    """A promotion must arrive with every structure validate.py requires."""

    def test_promoted_note_has_required_frontmatter(self, mp, projects):
        mp.promote_candidates({"good topic": (3, "Good Topic")})
        note = projects / "good-topic" / "00 Top Note.md"
        content = note.read_text()
        for key in ("status: active", "priority: medium", "next-action:"):
            assert key in content

    def test_promoted_note_is_listed_in_projects_index(self, mp, projects):
        mp.promote_candidates({"good topic": (3, "Good Topic")})
        index = projects / "projects.md"
        assert index.is_file()
        row = index.read_text()
        assert "[[good-topic/00 Top Note\\|Good Topic]]" in row
        # The row sits under the Active section, above Paused/Ideas.
        lines = row.splitlines()
        row_at = next(i for i, ln in enumerate(lines) if "good-topic" in ln)
        active_at = next(i for i, ln in enumerate(lines) if ln.strip() == "## Active")
        assert row_at > active_at

    def test_existing_index_rows_are_preserved(self, mp, projects):
        index = projects / "projects.md"
        index.write_text(
            "# Projects\n\n## Active\n\n"
            "| Project | Status | Priority | Next Action |\n"
            "|---------|--------|----------|-------------|\n"
            "| [[existing/00 Top Note\\|Existing]] | Active | Low | Keep going |\n"
            "\n## Paused\n\n"
            "| Project | Status | Priority | Next Action |\n"
            "|---------|--------|----------|-------------|\n"
        )
        mp.promote_candidates({"good topic": (3, "Good Topic")})
        content = index.read_text()
        assert "[[existing/00 Top Note" in content
        assert "[[good-topic/00 Top Note" in content
        assert content.index("good-topic") < content.index("## Paused")

    def test_missing_index_is_created_with_active_section(self, mp, projects):
        mp.promote_candidates({"good topic": (3, "Good Topic")})
        content = (projects / "projects.md").read_text()
        assert "## Active" in content
        assert "good-topic" in content

    def test_failed_write_does_not_touch_projects_index(self, mp, projects, monkeypatch):
        def failing_open(self, *args, **kwargs):
            raise OSError("simulated write failure")

        monkeypatch.setattr(pathlib.Path, "open", failing_open)
        created = mp.promote_candidates({"foo bar": (3, "foo bar")})
        assert created == []
        assert not (projects / "projects.md").exists()

    def test_active_section_without_table_gets_one(self, mp, projects):
        index = projects / "projects.md"
        index.write_text("# Projects\n\n## Active\n\n## Paused\n")
        mp.promote_candidates({"good topic": (3, "Good Topic")})
        lines = index.read_text().splitlines()
        assert "| Project | Status | Priority | Next Action |" in lines
        assert "|---------|--------|----------|-------------|" in lines
        row = next(ln for ln in lines if "good-topic" in ln)
        # The row lands inside a real table: header above it.
        assert lines.index("| Project | Status | Priority | Next Action |") < lines.index(row)

    def test_active_heading_at_end_of_file_gets_table(self, mp, projects):
        index = projects / "projects.md"
        index.write_text("# Projects\n\n## Active\n")
        mp.promote_candidates({"good topic": (3, "Good Topic")})
        content = index.read_text()
        assert "good-topic" in content
        assert "| Project | Status | Priority | Next Action |" in content

    def test_brackets_in_title_do_not_break_the_wikilink(self, mp, projects):
        from vault import extract_wikilinks

        mp.promote_candidates({"fix wip thing": (3, "Fix [WIP] thing")})
        content = (projects / "projects.md").read_text()
        row = next(ln for ln in content.splitlines() if "fix-wip-thing" in ln)
        links = extract_wikilinks(row)
        assert links == ["fix-wip-thing/00 Top Note"]

    def test_promoted_note_carries_last_reviewed(self, mp, projects):
        mp.promote_candidates({"good topic": (3, "Good Topic")})
        content = (projects / "good-topic" / "00 Top Note.md").read_text()
        assert "last-reviewed:" in content
