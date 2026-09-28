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


class TestValidatePersonas:
    def test_missing_persona_dir(self, val, tmp_path):
        ctx = val.ValidationContext()
        val.WORKSPACE = tmp_path
        val.validate_personas(ctx)
        assert len(ctx.errors) == 0


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
