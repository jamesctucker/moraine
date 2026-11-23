"""Tests for scripts/workspace/manifest.py — the one schema both manifests answer to."""

from pathlib import Path

import manifest as mf
import pytest
import yaml
from test_helpers import PACK_YAML, build_workspace

BASE = "version: 1\nharnesses: [opencode]\npacks: []\nmcp: {}\n"


def problems_of(root, manifest=BASE, packs=None):
    """Every problem load_manifests finds in a throwaway workspace."""
    workspace = build_workspace(root, manifest=manifest, packs=packs)
    with pytest.raises(mf.ManifestError) as caught:
        mf.load_manifests(workspace)
    return caught.value.problems


class TestManifestSchema:
    def test_a_valid_manifest_loads(self, tmp_path):
        manifest, packs = mf.load_manifests(build_workspace(tmp_path))

        assert (manifest.harnesses, manifest.packs, manifest.mcp) == (("opencode",), (), {})
        assert packs == {}

    def test_a_missing_manifest_is_reported(self, tmp_path):
        with pytest.raises(mf.ManifestError) as caught:
            mf.load_manifests(tmp_path)

        assert "moraine.yaml: not found" in caught.value.problems[0]

    @pytest.mark.parametrize(
        "text, problem",
        [
            ("version: 2\n", "version 2 is not supported"),
            ("packs: []\n", "missing required key 'version'"),
            ("version: 1\nharnesses: [vim]\n", "unknown name 'vim'"),
            ("version: 1\nharnesses: [opencode, opencode]\n", "must be unique"),
            ("version: 1\nharnesses: opencode\n", "must be a list of names"),
            ("version: 1\npacks: [local]\n", "'local' is always enabled"),
            ("version: 1\npacks: [ghost]\n", "unknown pack 'ghost'"),
            ("version: 1\nsurprise: true\n", "unknown key 'surprise'"),
            ("version: 1\nmcp:\n  x:\n    type: local\n", "non-empty 'command'"),
            ("version: 1\nmcp:\n  x:\n    type: remote\n", "needs a 'url'"),
            ("version: 1\nmcp:\n  x:\n    type: carrier-pigeon\n", "type must be 'local' or 'remote'"),
            ("- a\n- list\n", "must be a mapping"),
        ],
    )
    def test_a_bad_manifest_names_the_problem(self, tmp_path, text, problem):
        found = problems_of(tmp_path, text)

        assert any(problem in item for item in found), found

    def test_every_problem_in_a_file_is_reported_in_one_go(self, tmp_path):
        found = problems_of(tmp_path, "version: 1\nharnesses: [vim]\nsurprise: true\n")

        assert len(found) == 2

    def test_names_are_checked_before_what_depends_on_them(self, tmp_path):
        # Harnesses and servers are resolved through pack names.
        found = problems_of(tmp_path, "version: 1\nharnesses: [opencode]\npacks: [ghost, runner]\n", packs={
            "runner": {"yaml": PACK_YAML.format(name="runner") + "harnesses: [opencode]\n"},
        })

        assert found == ["moraine.yaml: unknown pack 'ghost'"]

    def test_harnesses_and_packs_may_be_left_out(self, tmp_path):
        manifest, _ = mf.load_manifests(build_workspace(tmp_path, "version: 1\n"))

        assert (manifest.harnesses, manifest.packs, manifest.mcp) == ((), (), {})


class TestPackSchema:
    @pytest.mark.parametrize(
        "extra, problem",
        [
            ("surprise: true\n", "unknown key 'surprise'"),
            ("requires: [ghost]\n", "requires unknown pack 'ghost'"),
            ("requires: [demo]\n", "requires unknown pack 'demo'"),
            ("harnesses: [vim]\n", "unknown name 'vim'"),
            ("harnesses: [any, opencode]\n", "'any' cannot be combined"),
            ("harnesses: []\n", "cannot be empty"),
            ("prereqs:\n  - cmd: uvx\n", "missing required key 'why'"),
            ("prereqs:\n  - just a string\n", "must be a mapping"),
            ("prereqs:\n  - cmd: uvx\n    why: speed\n    install:\n      plan9: pkg add uv\n", "unknown platform 'plan9'"),
            ("prereqs:\n  - cmd: uvx\n    why: speed\n    install: [a, b]\n", "must be a command"),
            ("jobs: [jobs/missing.yaml]\n", "is not a file in the pack"),
            ("jobs: [../moraine.yaml]\n", "is not a file in the pack"),
            ("mcp:\n  x:\n    type: local\n    command: []\n", "non-empty 'command'"),
        ],
    )
    def test_a_bad_pack_names_the_problem(self, tmp_path, extra, problem):
        packs = {"demo": {"yaml": PACK_YAML.format(name="demo") + extra}}

        found = problems_of(tmp_path, packs=packs)

        assert any(problem in item for item in found), found

    def test_the_name_must_match_the_folder(self, tmp_path):
        found = problems_of(tmp_path, packs={"demo": {"yaml": PACK_YAML.format(name="other")}})

        assert "'other' does not match the folder 'demo'" in found[0]

    def test_the_description_is_required(self, tmp_path):
        found = problems_of(tmp_path, packs={"demo": {"yaml": "name: demo\n"}})

        assert "missing required key 'description'" in found[0]

    def test_defaults_are_any_harness_and_no_requirements(self, tmp_path):
        _, packs = mf.load_manifests(build_workspace(tmp_path, packs={"demo": {}}))

        assert (packs["demo"].harnesses, packs["demo"].requires, packs["demo"].jobs) == (("any",), (), ())

    @pytest.mark.parametrize(
        "install_clause, expected",
        [
            ("    install: uv tool install thing\n", {"macos": "uv tool install thing", "linux": "uv tool install thing"}),
            (
                "    install:\n      macos: brew install thing\n      linux: curl -Ls thing\n",
                {"macos": "brew install thing", "linux": "curl -Ls thing"},
            ),
            ("", {}),
        ],
    )
    def test_install_is_one_command_or_one_per_platform(self, tmp_path, install_clause, expected):
        pack_yaml = PACK_YAML.format(name="demo") + "prereqs:\n  - cmd: thing\n    why: speed\n" + install_clause
        _, packs = mf.load_manifests(build_workspace(tmp_path, packs={"demo": {"yaml": pack_yaml}}))

        assert packs["demo"].prereqs[0].cmd == "thing"
        assert {platform: command for platform, command in packs["demo"].prereqs[0].install.items() if platform in expected} == expected


class TestCrossChecks:
    def test_a_requires_cycle_is_reported_once(self, tmp_path):
        packs = {
            "alpha": {"yaml": PACK_YAML.format(name="alpha") + "requires: [beta]\n"},
            "beta": {"yaml": PACK_YAML.format(name="beta") + "requires: [alpha]\n"},
        }

        assert problems_of(tmp_path, packs=packs) == ["requires cycle: alpha -> beta -> alpha"]

    def test_enabling_a_pack_enables_what_it_requires(self, tmp_path):
        packs = {
            "alpha": {"yaml": PACK_YAML.format(name="alpha") + "requires: [beta]\n"},
            "beta": {},
            "gamma": {},
        }
        manifest, shipped = mf.load_manifests(
            build_workspace(tmp_path, "version: 1\npacks: [alpha]\n", packs=packs)
        )

        assert list(mf.enabled_packs(manifest.packs, shipped)) == ["alpha", "beta"]

    def test_a_pack_needing_a_harness_is_rejected_without_it(self, tmp_path):
        packs = {"runner": {"yaml": PACK_YAML.format(name="runner") + "harnesses: [opencode]\n"}}

        found = problems_of(tmp_path, "version: 1\nharnesses: []\npacks: [runner]\n", packs=packs)

        assert found == ["packs/runner/pack.yaml: needs the opencode harness, but moraine.yaml lists none"]

    def test_the_same_pack_loads_once_its_harness_is_listed(self, tmp_path):
        packs = {"runner": {"yaml": PACK_YAML.format(name="runner") + "harnesses: [opencode]\n"}}

        mf.load_manifests(build_workspace(tmp_path, "version: 1\nharnesses: [opencode]\npacks: [runner]\n", packs=packs))

    def test_an_enabled_pack_that_runs_anywhere_needs_no_harness_listed(self, tmp_path):
        mf.load_manifests(build_workspace(tmp_path, "version: 1\npacks: []\n", packs={"runner": {}}))

    def test_a_server_shared_by_a_pack_and_the_user_is_an_error(self, tmp_path):
        server = "  shared:\n    type: remote\n    url: https://example.com/mcp\n"
        manifest = f"version: 1\npacks: [demo]\nmcp:\n{server}"
        packs = {"demo": {"yaml": PACK_YAML.format(name="demo") + "mcp:\n" + server}}

        found = problems_of(tmp_path, manifest, packs=packs)

        assert found == ["MCP server 'shared' is defined in both packs/demo/pack.yaml and moraine.yaml; rename one"]

    def test_a_server_shared_by_two_enabled_packs_is_an_error(self, tmp_path):
        server = "mcp:\n  shared:\n    type: remote\n    url: https://example.com/mcp\n"
        packs = {"alpha": {"yaml": PACK_YAML.format(name="alpha") + server}, "beta": {"yaml": PACK_YAML.format(name="beta") + server}}

        found = problems_of(tmp_path, "version: 1\npacks: [alpha, beta]\n", packs=packs)

        assert "defined in both packs/alpha/pack.yaml and packs/beta/pack.yaml" in found[0]

    def test_a_disabled_pack_cannot_collide_with_the_user(self, tmp_path):
        server = "  shared:\n    type: remote\n    url: https://example.com/mcp\n"
        manifest = f"version: 1\npacks: []\nmcp:\n{server}"
        packs = {"demo": {"yaml": PACK_YAML.format(name="demo") + "mcp:\n" + server}}

        mf.load_manifests(build_workspace(tmp_path, manifest, packs=packs))


class TestPrereqs:
    def test_a_command_on_path_is_met(self, monkeypatch):
        monkeypatch.setattr(mf.shutil, "which", lambda cmd: "/usr/bin/uvx" if cmd == "uvx" else None)

        assert mf.prereq_met("uvx")
        assert not mf.prereq_met("no-such-tool")

    def test_a_desktop_app_counts_as_installed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mf.shutil, "which", lambda cmd: None)
        monkeypatch.setattr(mf.Path, "home", lambda: tmp_path)

        assert not mf.prereq_met("demovault")
        (tmp_path / "Applications" / "Demovault.app").mkdir(parents=True)
        assert mf.prereq_met("demovault")

    def test_missing_prereqs_lists_what_is_absent(self, monkeypatch):
        monkeypatch.setattr(mf.shutil, "which", lambda cmd: cmd == "uvx")
        pack = mf.Pack("demo", Path("."), "demo", prereqs=(mf.Prereq("uvx", "speed"), mf.Prereq("node", "clones")))

        assert [prereq.cmd for prereq in mf.missing_prereqs(pack)] == ["node"]

    @pytest.mark.parametrize(
        "platform, expected",
        [("darwin", "brew install thing"), ("linux", "curl -Ls thing"), ("win32", None)],
    )
    def test_the_install_hint_follows_the_platform(self, monkeypatch, platform, expected):
        prereq = mf.Prereq("thing", "speed", {"macos": "brew install thing", "linux": "curl -Ls thing"})
        monkeypatch.setattr(mf.sys, "platform", platform)

        assert mf.install_hint(prereq) == expected


class TestWritePackList:
    def test_a_flow_list_is_replaced_and_every_other_byte_survives(self, tmp_path):
        path = tmp_path / "moraine.yaml"
        path.write_text("# mine\nversion: 1\nharnesses: [opencode]   # keep\npacks: []   # enable what you use\n")

        mf.write_pack_list(path, ["demo"])

        assert path.read_text() == "# mine\nversion: 1\nharnesses: [opencode]   # keep\npacks: [demo]   # enable what you use\n"

    def test_a_block_list_is_replaced(self, tmp_path):
        path = tmp_path / "moraine.yaml"
        path.write_text("version: 1\npacks:\n  - alpha\n  - beta\nmcp: {}\n")

        mf.write_pack_list(path, ["gamma"])

        assert path.read_text() == "version: 1\npacks:\n  [gamma]\nmcp: {}\n"
        assert yaml.safe_load(path.read_text()) == {"version": 1, "packs": ["gamma"], "mcp": {}}

    def test_an_absent_key_is_appended(self, tmp_path):
        path = tmp_path / "moraine.yaml"
        path.write_text("version: 1\n")

        mf.write_pack_list(path, ["demo"])

        assert path.read_text() == "version: 1\npacks: [demo]\n"
        assert yaml.safe_load(path.read_text()) == {"version": 1, "packs": ["demo"]}

    def test_a_comment_before_a_block_list_survives(self, tmp_path):
        path = tmp_path / "moraine.yaml"
        path.write_text("version: 1\npacks:   # enable what you use\n  - alpha\n")

        mf.write_pack_list(path, ["beta"])

        assert path.read_text() == "version: 1\npacks:   # enable what you use\n  [beta]\n"
        assert yaml.safe_load(path.read_text()) == {"version": 1, "packs": ["beta"]}

    def test_an_edit_that_cannot_be_made_leaves_the_file_alone(self, tmp_path):
        # Duplicate keys: YAML takes the last one, so rewriting the first cannot win.
        path = tmp_path / "moraine.yaml"
        original = "version: 1\npacks: []\npacks: [alpha]\n"
        path.write_text(original)

        with pytest.raises(mf.ManifestError, match="edit it by hand"):
            mf.write_pack_list(path, ["beta"])

        assert path.read_text() == original
