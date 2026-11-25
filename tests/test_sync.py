"""Tests for scripts/workspace/sync.py — what sync links, writes, removes, and refuses."""

import json
import os

import manifest as mf
import pytest
import sync
from test_helpers import PACK_YAML, build_workspace

DEMO_MCP = "mcp:\n  demo:\n    type: local\n    command: [uvx, demo]\n"


def run_sync(workspace):
    """Sync a throwaway workspace, keeping cron state inside it."""
    return sync.run(workspace, cron_state=workspace / "cron-state")


def listing(*packs):
    """A manifest that lists the OpenCode harness and the given packs."""
    return f"version: 1\nharnesses: [opencode]\npacks: [{', '.join(packs)}]\n"


def enable(workspace, *packs):
    (workspace / "moraine.yaml").write_text(listing(*packs))


def skill_link(workspace, skill_id):
    return workspace / ".agents" / "skills" / skill_id


class TestSkills:
    def test_links_whole_skill_folders_by_relative_target(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"skills": ["alpha"]}})
        (workspace / "packs" / "demo" / "skills" / "alpha" / "reference.md").write_text("a sibling file")

        result = run_sync(workspace)

        link = skill_link(workspace, "alpha")
        assert os.readlink(link) == "../../packs/demo/skills/alpha"
        # The folder is the link, never SKILL.md: Codex skips a symlinked file.
        assert not (link / "SKILL.md").is_symlink()
        assert (link / "SKILL.md").is_file()
        assert (link / "reference.md").is_file()
        assert [change.detail for change in result.changes if change.path == link] == ["link .agents/skills/alpha"]

    def test_sync_is_idempotent(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"skills": ["alpha"], "yaml": PACK_YAML.format(name="demo") + DEMO_MCP}})

        first = run_sync(workspace)

        assert first.changes
        assert run_sync(workspace).changes == []

    def test_a_core_only_workspace_has_nothing_to_do(self, tmp_path):
        workspace = build_workspace(tmp_path, packs={"demo": {"skills": ["alpha"]}})

        assert run_sync(workspace).changes == []
        assert not skill_link(workspace, "alpha").exists()

    def test_removes_only_the_links_it_manages(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"skills": ["alpha"]}})
        run_sync(workspace)
        (workspace / "elsewhere" / "mine").mkdir(parents=True)
        (workspace / "elsewhere" / "mine" / "SKILL.md").write_text("# mine\n")
        skill_link(workspace, "mine").symlink_to("../../elsewhere/mine")
        enable(workspace)

        result = run_sync(workspace)

        assert not skill_link(workspace, "alpha").exists()  # managed, and its pack is now off
        assert os.readlink(skill_link(workspace, "mine")) == "../../elsewhere/mine"  # the user's own link
        assert skill_link(workspace, "session-handoff").is_dir()  # core stays a real folder
        assert [change.detail for change in result.changes] == [
            "remove stale .agents/skills/alpha",
            "rewrite the managed block in .git/info/exclude",
        ]

    @pytest.mark.parametrize(
        "where, other",
        [("core", ".agents/skills/alpha"), ("local", "packs/local/skills/alpha"), ("pack", "packs/rival/skills/alpha")],
    )
    def test_a_skill_id_claimed_twice_is_refused_and_names_both(self, tmp_path, where, other):
        workspace = build_workspace(
            tmp_path,
            listing("demo", "rival"),
            packs={"demo": {"skills": ["alpha", "fresh"]}, "rival": {"skills": ["alpha"] if where == "pack" else []}},
        )
        if where == "core":
            (workspace / ".agents" / "skills" / "alpha").mkdir()
            (workspace / ".agents" / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: core\n---\n")
        if where == "local":
            (workspace / "packs" / "local" / "skills" / "alpha").mkdir(parents=True)
            (workspace / "packs" / "local" / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: mine\n---\n")

        with pytest.raises(sync.SyncError) as caught:
            run_sync(workspace)

        [problem] = caught.value.problems
        assert "skill 'alpha' exists in both" in problem
        assert other in problem
        assert "packs/demo/skills/alpha" in problem
        assert not skill_link(workspace, "fresh").exists()  # refused before anything was written

    def test_a_foreign_link_sitting_at_a_wanted_id_is_not_overwritten(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"skills": ["alpha"]}})
        skill_link(workspace, "alpha").symlink_to("../../elsewhere/alpha")

        with pytest.raises(sync.SyncError, match="sync does not own it"):
            run_sync(workspace)

        assert os.readlink(skill_link(workspace, "alpha")) == "../../elsewhere/alpha"

    def test_follows_a_skill_that_moves_to_another_pack(self, tmp_path):
        packs = {"first": {"skills": ["alpha"]}, "second": {"skills": ["alpha"]}}
        workspace = build_workspace(tmp_path, listing("first"), packs=packs)
        run_sync(workspace)
        enable(workspace, "second")

        result = run_sync(workspace)

        assert os.readlink(skill_link(workspace, "alpha")) == "../../packs/second/skills/alpha"
        assert [change.kind for change in result.changes if change.path == skill_link(workspace, "alpha")] == ["remove", "link"]

    def test_a_link_checked_out_as_text_is_repaired(self, tmp_path):
        # core.symlinks=false stores a symlink as a one-line text file.
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"skills": ["alpha"]}})
        skill_link(workspace, "alpha").write_text("../../packs/demo/skills/alpha\n")

        run_sync(workspace)

        assert os.readlink(skill_link(workspace, "alpha")) == "../../packs/demo/skills/alpha"


class TestExcludeBlock:
    def test_the_block_lists_the_links_and_nothing_else_changes(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"skills": ["alpha", "beta"]}})
        exclude = workspace / ".git" / "info" / "exclude"
        exclude.parent.mkdir(parents=True)
        exclude.write_text("# my rules\n*.secret\n")

        run_sync(workspace)

        assert exclude.read_text() == (
            "# my rules\n*.secret\n# moraine:managed\n/.agents/skills/alpha\n/.agents/skills/beta\n# moraine:managed end\n"
        )

        exclude.write_text(exclude.read_text().replace("*.secret\n", "*.secret\n*.local\n"))
        assert run_sync(workspace).changes == []
        assert exclude.read_text().startswith("# my rules\n*.secret\n*.local\n")

    def test_the_file_and_block_are_created_when_missing(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"skills": ["alpha"]}})

        run_sync(workspace)

        assert (workspace / ".git" / "info" / "exclude").read_text() == (
            "# moraine:managed\n/.agents/skills/alpha\n# moraine:managed end\n"
        )

    def test_a_core_only_workspace_gets_no_block(self, tmp_path):
        workspace = build_workspace(tmp_path)

        run_sync(workspace)

        assert not (workspace / ".git" / "info" / "exclude").exists()

    def test_an_unterminated_block_is_repaired(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"skills": ["alpha"]}})
        exclude = workspace / ".git" / "info" / "exclude"
        exclude.parent.mkdir(parents=True)
        exclude.write_text("*.secret\n# moraine:managed\n/stale/link\n")

        run_sync(workspace)

        assert exclude.read_text() == (
            "*.secret\n# moraine:managed\n/.agents/skills/alpha\n# moraine:managed end\n"
        )


def opencode_config(workspace, text):
    path = workspace / ".opencode" / "opencode.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text)
    return path


RENDERED_DEMO = '{\n      "demo": {\n        "type": "local",\n        "command": [\n          "uvx",\n          "demo"\n        ]\n      }\n    }'


class TestHarnessConfigs:
    """MCP output for Claude (.mcp.json) and Codex (.codex/config.toml)."""

    BOTH_SERVERS = (
        "mcp:\n"
        "  demo:\n    type: local\n    command: [uvx, demo]\n"
        "  linear:\n    type: remote\n    url: https://mcp.linear.app/mcp\n"
    )

    def _workspace(self, tmp_path, harness):
        manifest = f"version: 1\nharnesses: [{harness}]\npacks: [demo]\n" + self.BOTH_SERVERS
        return build_workspace(tmp_path, manifest, packs={"demo": {"skills": ["alpha"]}})

    def test_claude_gets_an_mcp_json_with_command_and_args(self, tmp_path):
        workspace = self._workspace(tmp_path, "claude")

        run_sync(workspace)

        written = json.loads((workspace / ".mcp.json").read_text())["mcpServers"]
        assert written == {
            "demo": {"command": "uvx", "args": ["demo"]},
            "linear": {"type": "http", "url": "https://mcp.linear.app/mcp"},
        }

    def test_codex_gets_a_config_toml(self, tmp_path):
        workspace = self._workspace(tmp_path, "codex")

        run_sync(workspace)

        written = (workspace / ".codex" / "config.toml").read_text()
        assert '[mcp_servers.demo]' in written
        assert 'command = "uvx"' in written
        assert 'args = ["demo"]' in written
        assert '[mcp_servers.linear]' in written
        assert 'url = "https://mcp.linear.app/mcp"' in written

    def test_no_config_is_written_for_an_unlisted_harness(self, tmp_path):
        workspace = self._workspace(tmp_path, "opencode")

        run_sync(workspace)

        assert not (workspace / ".mcp.json").exists()
        assert not (workspace / ".codex").exists()

    def test_an_empty_server_set_writes_empty_configs(self, tmp_path):
        workspace = build_workspace(tmp_path, "version: 1\nharnesses: [claude, codex]\npacks: [demo]\n", packs={"demo": {"skills": ["alpha"]}})
        (workspace / ".mcp.json").write_text('{"mcpServers": {"stale": {}}}\n')
        (workspace / ".codex" / "config.toml").parent.mkdir(exist_ok=True)
        (workspace / ".codex" / "config.toml").write_text("[mcp_servers.stale]\ncommand = \"x\"\n")

        run_sync(workspace)

        assert json.loads((workspace / ".mcp.json").read_text())["mcpServers"] == {}
        assert "stale" not in (workspace / ".codex" / "config.toml").read_text()

    def test_a_server_name_with_spaces_is_quoted_in_toml(self, tmp_path):
        manifest = "version: 1\nharnesses: [codex]\npacks: []\nmcp:\n  my server:\n    type: local\n    command: [uvx]\n"
        workspace = build_workspace(tmp_path, manifest)

        run_sync(workspace)

        assert '[mcp_servers."my server"]' in (workspace / ".codex" / "config.toml").read_text()


class TestClaudeSkillsLink:
    def test_the_link_is_created_for_claude(self, tmp_path):
        workspace = build_workspace(tmp_path, "version: 1\nharnesses: [claude]\npacks: []\n")

        run_sync(workspace)

        link = workspace / ".claude" / "skills"
        assert os.readlink(link) == "../.agents/skills"

    def test_the_link_is_removed_when_claude_is_unlisted(self, tmp_path):
        workspace = build_workspace(tmp_path, "version: 1\nharnesses: [claude]\npacks: []\n")
        run_sync(workspace)

        (workspace / "moraine.yaml").write_text("version: 1\nharnesses: [opencode]\npacks: []\n")
        run_sync(workspace)

        assert not (workspace / ".claude" / "skills").exists()

    def test_a_real_directory_is_left_alone(self, tmp_path):
        workspace = build_workspace(tmp_path, "version: 1\nharnesses: [claude]\npacks: []\n")
        skills = workspace / ".claude" / "skills"
        skills.mkdir(parents=True)
        (skills / "mine").mkdir()

        result = run_sync(workspace)

        assert (skills / "mine").is_dir()
        assert not skills.is_symlink()
        assert not any(".claude" in change.detail for change in result.changes)


class TestMcpServers:
    def test_only_the_servers_object_changes(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"yaml": PACK_YAML.format(name="demo") + DEMO_MCP}})
        original = (
            "{\n"
            '  "$schema": "https://opencode.ai/config.json",\n'
            '  "permissions": [{"action": "shell", "resource": "*", "effect": "allow"}],\n'
            '  "mcp": {\n'
            '    "servers": {\n'
            '      "old": {"type": "remote", "url": "https://example.com/mcp"}\n'
            "    }\n"
            "  }\n"
            "}\n"
        )
        config = opencode_config(workspace, original)

        run_sync(workspace)

        head, _, tail = original.partition('    "servers": {\n')
        after = config.read_text()
        assert after == head + '    "servers": ' + RENDERED_DEMO + "\n" + tail.partition("    }\n")[2]
        assert json.loads(after)["mcp"]["servers"] == {"demo": {"type": "local", "command": ["uvx", "demo"]}}

    def test_pack_and_user_servers_are_merged(self, tmp_path):
        manifest = listing("demo") + "mcp:\n  linear:\n    type: remote\n    url: https://mcp.linear.app/mcp\n"
        workspace = build_workspace(tmp_path, manifest, packs={"demo": {"yaml": PACK_YAML.format(name="demo") + DEMO_MCP}})
        config = opencode_config(workspace, '{\n  "mcp": {\n    "servers": {}\n  }\n}\n')

        run_sync(workspace)

        assert json.loads(config.read_text())["mcp"]["servers"] == {
            "demo": {"type": "local", "command": ["uvx", "demo"]},
            "linear": {"type": "remote", "url": "https://mcp.linear.app/mcp"},
        }

    def test_servers_are_added_to_an_mcp_object_without_them(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"yaml": PACK_YAML.format(name="demo") + DEMO_MCP}})
        config = opencode_config(workspace, '{\n  "mcp": {\n    "keep": true\n  }\n}\n')

        run_sync(workspace)

        assert config.read_text() == (
            "{\n"
            '  "mcp": {\n'
            '    "servers": ' + RENDERED_DEMO + ",\n"
            '    "keep": true\n'
            "  }\n"
            "}\n"
        )

    def test_an_empty_config_gains_an_mcp_block(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"yaml": PACK_YAML.format(name="demo") + DEMO_MCP}})
        config = opencode_config(workspace, "{\n}\n")

        run_sync(workspace)

        assert config.read_text() == (
            "{\n"
            '  "mcp": {\n'
            '    "servers": {\n'
            '      "demo": {\n'
            '        "type": "local",\n'
            '        "command": [\n'
            '          "uvx",\n'
            '          "demo"\n'
            "        ]\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )

    def test_four_space_indent_is_kept(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"yaml": PACK_YAML.format(name="demo") + DEMO_MCP}})
        config = opencode_config(workspace, '{\n    "mcp": {\n        "servers": {}\n    }\n}\n')

        run_sync(workspace)

        assert config.read_text() == (
            "{\n"
            '    "mcp": {\n'
            '        "servers": {\n'
            '            "demo": {\n'
            '                "type": "local",\n'
            '                "command": [\n'
            '                    "uvx",\n'
            '                    "demo"\n'
            "                ]\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "}\n"
        )

    def test_a_server_no_longer_enabled_is_removed(self, tmp_path):
        workspace = build_workspace(tmp_path)
        config = opencode_config(workspace, '{\n  "mcp": {\n    "servers": {\n      "old": {"type": "remote", "url": "https://example.com"}\n    }\n  }\n}\n')

        run_sync(workspace)

        assert config.read_text() == '{\n  "mcp": {\n    "servers": {}\n  }\n}\n'

    @pytest.mark.parametrize("text, problem", [("not json", "not valid JSON"), ("[1, 2]", "must be objects")])
    def test_a_config_that_cannot_be_edited_is_left_alone(self, tmp_path, text, problem):
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"yaml": PACK_YAML.format(name="demo") + DEMO_MCP}})
        config = opencode_config(workspace, text)

        with pytest.raises(sync.SyncError, match=problem):
            run_sync(workspace)

        assert config.read_text() == text

    def test_nothing_is_written_without_the_opencode_harness(self, tmp_path):
        workspace = build_workspace(tmp_path, "version: 1\nharnesses: []\npacks: [demo]\n", packs={"demo": {"yaml": PACK_YAML.format(name="demo") + DEMO_MCP}})
        original = "{\n  \"mcp\": {\n    \"servers\": {}\n  }\n}\n"
        config = opencode_config(workspace, original)

        run_sync(workspace)

        assert config.read_text() == original


class TestJobs:
    def test_jobs_wait_for_the_runner_pack(self, tmp_path):
        packs = {
            "scheduler": {"yaml": PACK_YAML.format(name="scheduler") + "jobs: [jobs/daily.yaml]\n", "jobs": ["daily.yaml"]},
            "automation": {"yaml": PACK_YAML.format(name="automation") + "harnesses: [opencode]\njobs: [jobs/recap.yaml]\n", "jobs": ["recap.yaml"]},
        }
        workspace = build_workspace(tmp_path, listing("scheduler"), packs=packs)

        waiting = run_sync(workspace)

        assert not (workspace / "cron-state" / "enabled.json").exists()
        assert waiting.notes == ["jobs skipped, the 'automation' pack is not enabled: packs/scheduler/jobs/daily.yaml"]

        enable(workspace, "scheduler", "automation")
        run_sync(workspace)

        assert json.loads((workspace / "cron-state" / "enabled.json").read_text()) == {
            "jobs": ["packs/automation/jobs/recap.yaml", "packs/scheduler/jobs/daily.yaml"]
        }

    def test_the_users_own_jobs_are_included(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("automation"), packs={
            "automation": {"yaml": PACK_YAML.format(name="automation") + "harnesses: [opencode]\n"},
        })
        (workspace / "packs" / "local" / "jobs").mkdir(parents=True)
        (workspace / "packs" / "local" / "jobs" / "mine.yaml").write_text("name: mine\n")

        run_sync(workspace)

        assert json.loads((workspace / "cron-state" / "enabled.json").read_text()) == {"jobs": ["packs/local/jobs/mine.yaml"]}

    def test_a_stale_job_list_is_removed_when_the_runner_is_disabled(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("automation"), packs={
            "automation": {"yaml": PACK_YAML.format(name="automation") + "harnesses: [opencode]\n"},
        })
        run_sync(workspace)
        enable(workspace)

        result = run_sync(workspace)

        assert not (workspace / "cron-state" / "enabled.json").exists()
        assert "remove" in result.changes[0].detail

    def test_two_packs_shipping_the_same_job_filename_is_an_error(self, tmp_path):
        # The runner installs job files by name alone, so a shared filename
        # would silently overwrite, unlike skills which collide loudly.
        packs = {
            "automation": {"yaml": PACK_YAML.format(name="automation") + "harnesses: [opencode]\njobs: [jobs/recap.yaml]\n", "jobs": ["recap.yaml"]},
            "scheduler": {"yaml": PACK_YAML.format(name="scheduler") + "jobs: [jobs/recap.yaml]\n", "jobs": ["recap.yaml"]},
        }
        workspace = build_workspace(tmp_path, listing("scheduler", "automation"), packs=packs)

        with pytest.raises(sync.SyncError, match="'recap.yaml' ships in both packs/automation/ and packs/scheduler/"):
            run_sync(workspace)

        assert not (workspace / "cron-state" / "enabled.json").exists()

    def test_job_filename_collisions_do_not_matter_without_the_runner(self, tmp_path):
        workspace = build_workspace(tmp_path, listing("scheduler", "other"), packs={
            "scheduler": {"yaml": PACK_YAML.format(name="scheduler") + "jobs: [jobs/recap.yaml]\n", "jobs": ["recap.yaml"]},
            "other": {"yaml": PACK_YAML.format(name="other") + "jobs: [jobs/recap.yaml]\n", "jobs": ["recap.yaml"]},
        })

        result = run_sync(workspace)

        assert not (workspace / "cron-state" / "enabled.json").exists()
        assert "jobs skipped" in result.notes[0]


class TestReport:
    def test_one_line_per_enabled_pack(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mf.shutil, "which", lambda cmd: cmd != "uvx")
        packs = {
            "demo": {"skills": ["alpha", "beta"], "yaml": PACK_YAML.format(name="demo") + "prereqs:\n  - cmd: uvx\n    why: speed\n"},
            "plain": {"skills": ["gamma"]},
        }
        workspace = build_workspace(tmp_path, listing("demo", "plain"), packs=packs)

        result = run_sync(workspace)

        assert result.packs == [
            "demo        enabled · 2 skills · prereqs missing: uvx",
            "plain       enabled · 1 skill · prereqs ok",
        ]

    def test_a_missing_prereq_is_noted_with_its_install_command(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mf.shutil, "which", lambda cmd: None)
        monkeypatch.setattr(mf.sys, "platform", "darwin")
        prereq = "prereqs:\n  - cmd: uvx\n    why: speed\n    install:\n      macos: brew install uv\n      linux: curl -Ls uv\n"
        workspace = build_workspace(tmp_path, listing("demo"), packs={"demo": {"yaml": PACK_YAML.format(name="demo") + prereq}})

        result = run_sync(workspace)

        assert result.notes == ["demo: 'uvx' is missing (speed); sync never installs. Install: brew install uv"]

    def test_servers_with_no_harness_listed_are_explained(self, tmp_path):
        workspace = build_workspace(tmp_path, "version: 1\npacks: [demo]\n", packs={
            "demo": {"yaml": PACK_YAML.format(name="demo") + DEMO_MCP},
        })

        result = run_sync(workspace)

        assert result.notes == [
            "no harness is listed in moraine.yaml, so the MCP servers were written nowhere; add the one you run"
        ]
