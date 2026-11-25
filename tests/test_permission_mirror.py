"""The Claude permission mirror must not drift from opencode.json.

Both lists are glob patterns over shell commands; the mirror maps each
`shell` rule in `.opencode/opencode.json` to the same pattern wrapped in
`Bash(...)`. Neither harness's list catches `rm -fr /`, `/bin/rm`, or
`bash -c '…'` — that limitation is documented in the README's trust model,
not compensated for here.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_claude_permissions_mirror_opencode_shell_rules():
    opencode = json.loads((ROOT / ".opencode" / "opencode.json").read_text())
    claude = json.loads((ROOT / ".claude" / "settings.json").read_text())

    def shell(effect):
        return sorted(
            rule["resource"]
            for rule in opencode["permissions"]
            if rule["action"] == "shell" and rule["effect"] == effect
        )

    def bash(effect):
        return sorted(rule[len("Bash(") : -len(")")] for rule in claude["permissions"][effect])

    assert bash("deny") == shell("deny")
    assert bash("ask") == shell("ask")


def test_the_mirror_holds_nothing_but_the_bash_rules():
    claude = json.loads((ROOT / ".claude" / "settings.json").read_text())

    assert set(claude) == {"permissions"}
    assert set(claude["permissions"]) == {"deny", "ask"}
    assert all(rule.startswith("Bash(") and rule.endswith(")") for rule in claude["permissions"]["deny"] + claude["permissions"]["ask"])
