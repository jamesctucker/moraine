"""Release checks for reviewed runtime and test dependency pins."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_downloads_are_exactly_pinned():
    # The packs that ship MCP servers pin the exact download.
    semble = (ROOT / "packs" / "semble" / "pack.yaml").read_text()

    assert 'command: ["uvx", "--from", "semble[mcp]==0.7.3", "semble"]' in semble


def test_opencode_config_ships_an_empty_server_block():
    # `moraine sync` owns mcp.servers; the committed template ships it empty.
    # Read from HEAD, not the working tree: CI's full job enables every pack
    # and sync legitimately fills the live block before pytest runs.
    template = subprocess.run(
        ["git", "show", "HEAD:.opencode/opencode.json"],
        capture_output=True, text=True, check=True,
    ).stdout

    assert json.loads(template)["mcp"]["servers"] == {}


def test_weekly_recap_uses_the_locked_pdf_package():
    recap = (ROOT / "packs" / "automation" / "jobs" / "weekly-recap.yaml").read_text()
    package = json.loads((ROOT / "packs" / "automation" / "runner" / "package.json").read_text())

    assert package["scripts"]["render:pdf"] == "md-to-pdf"
    assert 'bun run --cwd packs/automation/runner render:pdf "$PWD/wiki/' in recap
    assert "bunx md-to-pdf" not in recap
    assert "--no-sandbox" not in recap


def test_setup_installs_opencode_from_the_package_that_ships_2x():
    # `opencode-ai` stops at 1.19.x; OpenCode 2.x is published as `@opencode/cli`.
    setup = (ROOT / "scripts" / "setup").read_text()

    assert "opencode-ai" not in setup
    assert "@opencode/cli@${OPENCODE_VERSION}" in setup


def test_vitest_and_vite_are_on_reviewed_security_releases():
    package = json.loads((ROOT / "package.json").read_text())

    assert package["devDependencies"]["vitest"] == "5.1.1"
    assert package["devDependencies"]["vite"] == "7.3.7"
