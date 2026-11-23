"""Workspace utilities — single import surface for all scripts.

Every consumer imports from lib only:

    from lib import WORKSPACE, parse, extract_wikilinks

Frontmatter and vault implementations live in their own modules; `skill_dirs`
is defined here because it is neither.
"""

from pathlib import Path

from frontmatter import (
    ParseError,
    ParseErrorKind,
    ParseResult,
    parse,
    parse_detailed,
)
from vault import (
    VAULT,
    VAULT_DIRS,
    WORKSPACE,
    BrokenLink,
    WikilinkIndex,
    check_wikilinks,
    extract_wikilinks,
    walk_markdown,
)


def skill_dirs(skills_dir: Path) -> list[Path]:
    """Skill folders directly under `skills_dir`, sorted by ID.

    The layout is flat: one folder per skill, `<id>/SKILL.md`. Pack skills
    are symlinks into packs/, which a plain rglob does not follow.
    """
    if not skills_dir.is_dir():
        return []
    return sorted(entry for entry in skills_dir.iterdir() if (entry / "SKILL.md").is_file())


__all__ = [
    "BrokenLink",
    "ParseError",
    "ParseErrorKind",
    "ParseResult",
    "VAULT",
    "VAULT_DIRS",
    "WikilinkIndex",
    "WORKSPACE",
    "check_wikilinks",
    "extract_wikilinks",
    "parse",
    "parse_detailed",
    "skill_dirs",
    "walk_markdown",
]
