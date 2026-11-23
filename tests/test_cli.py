"""Tests for scripts/workspace/cli.py — the `moraine` command line."""

import pytest
import sync
import yaml
from cli import main
from test_helpers import PACK_YAML, build_workspace

RUNNER = PACK_YAML.format(name="runner") + "harnesses: [opencode]\nrequires: [demo]\n"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    # Never let a test touch the real ~/.moraine/cron.
    monkeypatch.setattr(sync, "default_cron_state", lambda: tmp_path / "cron-state")
    return build_workspace(tmp_path, packs={"demo": {"skills": ["alpha"]}, "runner": {"yaml": RUNNER}})


def enable(workspace, *packs):
    (workspace / "moraine.yaml").write_text(f"version: 1\nharnesses: [opencode]\npacks: [{', '.join(packs)}]\n")


def manifest_of(workspace):
    return yaml.safe_load((workspace / "moraine.yaml").read_text())


class TestSync:
    def test_sync_reports_each_enabled_pack_and_what_it_did(self, capsys, workspace):
        enable(workspace, "demo")

        assert main(["sync"], workspace) == 0

        out = capsys.readouterr().out
        assert "demo        enabled · 1 skill · prereqs ok" in out
        assert "link .agents/skills/alpha" in out
        assert (workspace / ".agents" / "skills" / "alpha").is_symlink()

    def test_a_second_sync_has_nothing_to_do(self, capsys, workspace):
        enable(workspace, "demo")
        main(["sync"], workspace)
        capsys.readouterr()

        assert main(["sync"], workspace) == 0

        assert "already in sync" in capsys.readouterr().out

    def test_a_core_only_workspace_says_so(self, capsys, workspace):
        assert main(["sync"], workspace) == 0

        assert "no packs enabled (core only); see: moraine packs list" in capsys.readouterr().out

    def test_dry_run_changes_nothing(self, capsys, workspace):
        enable(workspace, "demo")

        assert main(["sync", "--dry-run"], workspace) == 0

        assert "would link .agents/skills/alpha" in capsys.readouterr().out
        assert not (workspace / ".agents" / "skills" / "alpha").exists()

    def test_an_invalid_manifest_exits_one_and_prints_each_problem(self, capsys, tmp_path):
        broken = build_workspace(tmp_path, "version: 1\nharnesses: [vim]\nsurprise: true\n")

        assert main(["sync"], broken) == 1

        err = capsys.readouterr().err
        assert "error: moraine.yaml: harnesses: unknown name 'vim'" in err
        assert "error: moraine.yaml: unknown key 'surprise'" in err


class TestPacksList:
    def test_every_pack_is_listed_with_its_state(self, capsys, workspace):
        (workspace / "moraine.yaml").write_text("version: 1\nharnesses: []\npacks: []\n")

        assert main(["packs", "list"], workspace) == 0

        lines = capsys.readouterr().out.splitlines()
        assert lines[0].startswith("PACK")
        assert any(line.startswith("local        always") for line in lines)
        assert any(line.startswith("demo         no") and line.rstrip().endswith("any") for line in lines)
        assert any(line.startswith("runner       no") and line.endswith("opencode (not listed for this workspace)") for line in lines)
        assert any(line.strip() == "The runner pack." for line in lines)


class TestPacksEnable:
    def test_enable_edits_the_manifest_and_syncs(self, capsys, workspace):
        (workspace / "moraine.yaml").write_text("# mine\nversion: 1\nharnesses: [opencode]\npacks: []\n")

        assert main(["packs", "enable", "runner"], workspace) == 0

        # A pack arrives together with what it requires.
        assert (workspace / "moraine.yaml").read_text() == "# mine\nversion: 1\nharnesses: [opencode]\npacks: [demo, runner]\n"
        assert "runner      enabled · 0 skills · prereqs ok" in capsys.readouterr().out
        assert (workspace / ".agents" / "skills" / "alpha").is_symlink()

    def test_enable_refuses_a_pack_whose_harness_is_not_listed(self, capsys, tmp_path, monkeypatch):
        monkeypatch.setattr(sync, "default_cron_state", lambda: tmp_path / "cron-state")
        workspace = build_workspace(tmp_path, "version: 1\nharnesses: []\npacks: []\n", packs={
            "solo": {"yaml": PACK_YAML.format(name="solo") + "harnesses: [opencode]\n"},
        })

        assert main(["packs", "enable", "solo"], workspace) == 1

        out = capsys.readouterr().out
        assert "'solo' needs the opencode harness." in out
        assert "harnesses: [opencode]" in out
        assert manifest_of(workspace)["packs"] == []

    @pytest.mark.parametrize("name, reply", [("local", "'local' is always enabled"), ("ghost", "no pack 'ghost'. Available: local, demo, runner")])
    def test_enable_refuses_what_cannot_be_enabled(self, capsys, workspace, name, reply):
        assert main(["packs", "enable", name], workspace) == 1

        assert reply in capsys.readouterr().out
        assert manifest_of(workspace)["packs"] == []


class TestPacksDisable:
    def test_disable_removes_the_pack_unlinks_its_skills_and_syncs(self, capsys, workspace):
        enable(workspace, "demo")
        main(["sync"], workspace)
        capsys.readouterr()

        assert main(["packs", "disable", "demo"], workspace) == 0

        assert manifest_of(workspace)["packs"] == []
        assert "remove stale .agents/skills/alpha" in capsys.readouterr().out
        assert not (workspace / ".agents" / "skills" / "alpha").exists()

    def test_disable_refuses_while_an_enabled_pack_requires_it(self, capsys, workspace):
        enable(workspace, "demo", "runner")

        assert main(["packs", "disable", "demo"], workspace) == 1

        assert "refusing: 'demo' is required by runner. Disable those first." in capsys.readouterr().out
        assert manifest_of(workspace)["packs"] == ["demo", "runner"]

    def test_disabling_the_requirement_frees_the_pack_it_required(self, capsys, workspace):
        enable(workspace, "demo", "runner")
        assert main(["packs", "disable", "runner"], workspace) == 0
        capsys.readouterr()

        assert main(["packs", "disable", "demo"], workspace) == 0

        assert manifest_of(workspace)["packs"] == []

    @pytest.mark.parametrize("name, reply", [("local", "'local' is always enabled"), ("runner", "'runner' is not listed in moraine.yaml.")])
    def test_disable_refuses_what_cannot_be_disabled(self, capsys, workspace, name, reply):
        assert main(["packs", "disable", name], workspace) == 1

        assert reply in capsys.readouterr().out
