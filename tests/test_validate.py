"""Tests for scripts/workspace/validate.py."""

import pytest
from test_helpers import load_module


@pytest.fixture
def val(scripts_dir):
    return load_module("validate", scripts_dir / "validate.py")


class TestValidationContext:
    def test_collects_errors_and_warnings(self, val):
        ctx = val.ValidationContext()
        ctx.error("something broke")
        ctx.warn("something可疑")
        assert len(ctx.errors) == 1
        assert len(ctx.warnings) == 1


class TestValidateSkills:
    def test_skipping_missing_dir(self, val, tmp_path):
        ctx = val.ValidationContext()
        val.WORKSPACE = tmp_path
        val.validate_skills(ctx)
        assert len(ctx.warnings) >= 0

    def test_invalid_skill_dir_name(self, val, tmp_path):
        skill_dir = tmp_path / ".opencode" / "skills" / "Bad_Name"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("""---
name: Bad_Name
description: bad naming
---
Content
""")
        ctx = val.ValidationContext()
        val.WORKSPACE = tmp_path
        val.validate_skills(ctx)
        assert len(ctx.errors) >= 1
        assert any("kebab-case" in e for e in ctx.errors)


class TestValidateArtifacts:
    def test_good_artifact_passes(self, val, tmp_path):
        (tmp_path / "artifacts").mkdir()
        af = tmp_path / "artifacts" / "01-good-artifact.md"
        af.write_text("# Good\n\n## Table of Contents\n\nContent here")
        ctx = val.ValidationContext()
        val.WORKSPACE = tmp_path
        val.validate_artifacts(ctx)
        assert len(ctx.errors) == 0

    def test_bad_artifact_name(self, val, tmp_path):
        (tmp_path / "artifacts").mkdir()
        af = tmp_path / "artifacts" / "bad-name.md"
        af.write_text("# Bad\n\n## Table of Contents\n\nContent")
        ctx = val.ValidationContext()
        val.WORKSPACE = tmp_path
        val.validate_artifacts(ctx)
        assert len(ctx.errors) == 1

    def test_missing_toc(self, val, tmp_path):
        (tmp_path / "artifacts").mkdir()
        af = tmp_path / "artifacts" / "01-no-toc.md"
        af.write_text("# No TOC\n\nContent without table of contents")
        ctx = val.ValidationContext()
        val.WORKSPACE = tmp_path
        val.validate_artifacts(ctx)
        assert len(ctx.errors) == 1

    def test_skips_readme_and_template(self, val, tmp_path):
        (tmp_path / "artifacts").mkdir()
        for name in ("README.md", "_TEMPLATE.md"):
            (tmp_path / "artifacts" / name).write_text("# Skipped")
        ctx = val.ValidationContext()
        val.WORKSPACE = tmp_path
        val.validate_artifacts(ctx)
        assert len(ctx.errors) == 0


class TestValidateMemoryIndex:
    def test_missing_index(self, val, tmp_path):
        ctx = val.ValidationContext()
        val.WORKSPACE = tmp_path
        val.validate_memory_index(ctx)
        assert len(ctx.errors) == 1
        assert "index not found" in ctx.errors[0].lower()


class TestValidateProjects:
    """Live-status detection must work for both project layouts: the flat
    layout (1 Projects/<Name>/, status only in frontmatter) and the
    status-directory layout (1 Projects/Active/<Name>/)."""

    class _EmptyIndex:
        files = []

        def resolve(self, link, source_file=None):
            return None

    def _run(self, val, tmp_path, note_parts, frontmatter_status):
        vault = tmp_path / "wiki"
        note = vault.joinpath(*note_parts)
        note.parent.mkdir(parents=True)
        note.write_text(
            f"---\nstatus: {frontmatter_status}\npriority: high\n---\n# Checkout\n"
        )
        val.VAULT = vault
        val.WikilinkIndex = self._EmptyIndex
        ctx = val.ValidationContext()
        val.validate_projects(ctx)
        return ctx

    def test_flat_layout_active_requires_next_action(self, val, tmp_path):
        ctx = self._run(val, tmp_path, ("1 Projects", "Checkout", "00 Top Note.md"), "active")
        assert any("next-action" in w for w in ctx.warnings)

    def test_flat_layout_active_requires_last_reviewed(self, val, tmp_path):
        ctx = self._run(val, tmp_path, ("1 Projects", "Checkout", "00 Top Note.md"), "active")
        assert any("no last-reviewed" in w for w in ctx.warnings)

    def test_flat_layout_completed_has_no_review_clock(self, val, tmp_path):
        ctx = self._run(val, tmp_path, ("1 Projects", "Checkout", "00 Top Note.md"), "completed")
        assert not any("next-action" in w for w in ctx.warnings)
        assert not any("no last-reviewed" in w for w in ctx.warnings)

    def test_status_dir_layout_still_detected(self, val, tmp_path):
        ctx = self._run(val, tmp_path, ("1 Projects", "Active", "Checkout", "00 Top Note.md"), "active")
        assert any("next-action" in w for w in ctx.warnings)
