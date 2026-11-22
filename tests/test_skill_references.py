"""Static checks for bundled skill dependencies and local links."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".opencode" / "skills"
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
UNSHIPPED_REFERENCES = (
    "superpowers:",
    "setup-matt-pocock-skills",
    "codebase-design",
    "CONTEXT.md",
    "CONTEXT-FORMAT",
    "grill-with-docs",
    "docs/superpowers",
    "using-superpowers",
    "subagent-driven-development",
    "finishing-a-development-branch",
    "using-git-worktrees",
    "elements-of-style",
)


def test_skill_markdown_has_no_unshipped_dependencies():
    offenders = []
    for document in SKILLS.rglob("*.md"):
        text = document.read_text()
        offenders.extend(f"{document.relative_to(ROOT)}: {token}" for token in UNSHIPPED_REFERENCES if token in text)

    assert not offenders, "Unshipped skill references:\n" + "\n".join(offenders)


def test_skill_relative_markdown_links_resolve():
    broken = []
    for document in SKILLS.rglob("*.md"):
        for target in LINK.findall(document.read_text()):
            if not target or target.startswith(("#", "/", "mailto:")) or "://" in target:
                continue
            relative = unquote(target.split("#", 1)[0])
            if relative and not (document.parent / relative).resolve().exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")

    assert not broken, "Broken skill links:\n" + "\n".join(broken)
