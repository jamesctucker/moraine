"""Release checks for reviewed runtime and test dependency pins."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_downloads_are_exactly_pinned():
    config = json.loads((ROOT / ".opencode" / "opencode.json").read_text())
    brave = (ROOT / "scripts" / "mcp-servers" / "brave-search-mcp.sh").read_text()

    assert config["mcp"]["servers"]["semble"]["command"] == ["uvx", "--from", "semble[mcp]==0.7.3", "semble"]
    assert "@brave/brave-search-mcp-server@2.2.0" in brave


def test_weekly_recap_uses_the_locked_pdf_package():
    recap = (ROOT / "scheduled" / "weekly-recap.yaml").read_text()
    package = json.loads((ROOT / ".opencode" / "package.json").read_text())

    assert package["scripts"]["render:pdf"] == "md-to-pdf"
    assert "bun run --cwd .opencode render:pdf \"$PWD/wiki/" in recap
    assert "bunx md-to-pdf" not in recap
    assert "--no-sandbox" not in recap


def test_vitest_and_vite_are_on_reviewed_security_releases():
    package = json.loads((ROOT / "package.json").read_text())

    assert package["devDependencies"]["vitest"] == "4.1.11"
    assert package["devDependencies"]["vite"] == "7.3.7"
