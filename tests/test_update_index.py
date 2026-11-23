"""Tests for scripts/workspace/update-index.py."""

import pytest
from test_helpers import load_module


@pytest.fixture
def ui(scripts_dir):
    return load_module("update_index", scripts_dir / "update-index.py")


class TestExtractSection:
    def test_extracts_section_by_heading(self, ui):
        content = "## Active projects\n- project A\n- project B\n\n## Open threads\n- thread 1"
        result = ui.extract_section(content, "Active projects")
        assert "project A" in result
        assert "thread 1" not in result

    def test_returns_empty_for_missing(self, ui):
        assert ui.extract_section("# No matches", "Missing") == ""

    def test_prefix_match(self, ui):
        content = "## Recent decisions (2026-06-15)\n- decision 1"
        result = ui.extract_section(content, "Recent decisions", prefix_match=True)
        assert "decision 1" in result


class TestExtractAllDatedSections:
    def test_finds_multiple_dated_sections(self, ui):
        content = """## Recent decisions (2026-06-15)
- dec 1

## Recent decisions (2026-06-14)
- dec 2"""
        results = ui.extract_all_dated_sections(content, "Recent decisions")
        assert len(results) == 2

    def test_returns_empty_for_no_matches(self, ui):
        assert ui.extract_all_dated_sections("# Nothing", "Missing") == []


class TestExtractDecisionsFromSessions:
    def test_extracts_from_session_files(self, ui, tmp_path):
        session_file = tmp_path / "2026-06-15-test.md"
        session_file.write_text("## Decisions\n- decision 1\n- decision 2")
        decisions = ui.extract_decisions_from_sessions([session_file])
        assert "2026-06-15" in decisions
        assert len(decisions["2026-06-15"]) >= 2


class TestDecisionMerge:
    """Same-date manual and session decisions must both survive regeneration."""

    def test_manual_and_session_decisions_merged_under_one_date(self, ui, tmp_path, monkeypatch):
        index = tmp_path / "index.md"
        index.write_text("## Recent decisions (2026-06-15)\n- Manual decision\n")
        session = tmp_path / "2026-06-15-session.md"
        session.write_text("## Decisions\n- Session decision\n")
        monkeypatch.setattr(ui, "INDEX_PATH", index)

        new_index = ui.build_index([session], [], [], [])

        assert "## Recent decisions (2026-06-15)" in new_index
        assert "- Session decision" in new_index
        assert "- Manual decision" in new_index

    def test_duplicate_decision_lines_deduplicated(self, ui, tmp_path, monkeypatch):
        index = tmp_path / "index.md"
        index.write_text("## Recent decisions (2026-06-15)\n- Shared decision\n")
        session = tmp_path / "2026-06-15-session.md"
        session.write_text("## Decisions\n- Shared decision\n- Session only\n")
        monkeypatch.setattr(ui, "INDEX_PATH", index)

        new_index = ui.build_index([session], [], [], [])

        assert new_index.count("- Shared decision") == 1
        assert "- Session only" in new_index

    def test_manual_only_decision_survives(self, ui, tmp_path, monkeypatch):
        index = tmp_path / "index.md"
        index.write_text("## Recent decisions (2026-06-15)\n- Manual decision\n")
        monkeypatch.setattr(ui, "INDEX_PATH", index)

        new_index = ui.build_index([], [], [], [])

        assert "- Manual decision" in new_index


class TestGatherSkills:
    def test_finds_core_skills(self, ui, tmp_path, monkeypatch):
        skills_dir = tmp_path / ".agents" / "skills"
        skill = skills_dir / "tdd" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: tdd\ndescription: test driven\n---\nBody")
        monkeypatch.setattr(ui, "SKILLS_DIR", skills_dir)

        assert ui.gather_skills() == [("tdd", "test driven")]

    def test_follows_symlinked_pack_skills(self, ui, tmp_path, monkeypatch):
        # moraine sync links pack skills into .agents/skills as symlinks;
        # an rglob would stop at the link and report the skill missing.
        skills_dir = tmp_path / ".agents" / "skills"
        (skills_dir / "core-skill").mkdir(parents=True)
        (skills_dir / "core-skill" / "SKILL.md").write_text(
            "---\nname: core-skill\ndescription: core\n---\nBody")
        pack_skill = tmp_path / "packs" / "demo" / "skills" / "pack-skill"
        pack_skill.mkdir(parents=True)
        (pack_skill / "SKILL.md").write_text("---\nname: pack-skill\ndescription: packed\n---\nBody")
        (skills_dir / "pack-skill").symlink_to(pack_skill)
        monkeypatch.setattr(ui, "SKILLS_DIR", skills_dir)

        assert ui.gather_skills() == [("core-skill", "core"), ("pack-skill", "packed")]

    def test_name_falls_back_to_skill_directory(self, ui, tmp_path, monkeypatch):
        skills_dir = tmp_path / ".agents" / "skills"
        skill = skills_dir / "tdd" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\ndescription: no name field\n---\nBody")
        monkeypatch.setattr(ui, "SKILLS_DIR", skills_dir)

        assert ui.gather_skills() == [("tdd", "no name field")]

    def test_missing_skills_dir(self, ui, tmp_path, monkeypatch):
        monkeypatch.setattr(ui, "SKILLS_DIR", tmp_path / "does-not-exist")
        assert ui.gather_skills() == []


class TestIsKnownHeading:
    def test_known_headings(self, ui):
        for section in ui.KNOWN_SECTIONS:
            assert ui._is_known_heading(section)

    def test_unknown_heading(self, ui):
        assert not ui._is_known_heading("Random heading")

    def test_dated_known_heading(self, ui):
        assert ui._is_known_heading("Recent decisions (2026-06-15)")
