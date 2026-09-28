"""Vault primitives — walk, extract wikilinks, resolve, check."""

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
VAULT = WORKSPACE / "wiki"

# Well-known vault directories for path-based wikilink resolution.
VAULT_DIRS = ["0 Inbox", "1 Projects", "2 Areas", "3 Resources", "4 Archives"]

# Directories excluded from broken-wikilink checks:
# - Imported third-party content whose export-artifact links ([[starred]],
#   podcast names, etc.) will never resolve in the vault.
# - Daily Notes: journal entries use [[links]] as forward references to
#   notes that may never exist — an intentional Obsidian pattern, not breakage.
WIKILINK_CHECK_EXCLUDE_PREFIXES = ("3 Resources/Readwise/", "2 Areas/Daily Notes/")

# Unified wikilink regex: handles [[Link]], [[Link|Alias]], [[Link\|Alias]]
# (table-escaped pipe), and [[Link#block]] (block reference).
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[\\|#][^\]]+)?\]\]")


@dataclass(frozen=True)
class BrokenLink:
    source: Path
    link: str


def walk_markdown() -> list[Path]:
    return sorted(VAULT.rglob("*.md"))


def extract_wikilinks(content: str) -> list[str]:
    return _WIKILINK_RE.findall(content)


class WikilinkIndex:
    """Precomputed index of vault files for O(1) wikilink resolution."""

    def __init__(self) -> None:
        self._files = walk_markdown()
        self._file_set: set[Path] = set(self._files)
        self._by_stem: dict[str, list[Path]] = defaultdict(list)
        for f in self._files:
            self._by_stem[f.stem].append(f)

    @property
    def files(self) -> list[Path]:
        return self._files

    def resolve(self, link: str, source_file: Path | None = None) -> Path | None:
        """Resolve a wikilink to a file path, or None if unresolvable.

        Resolution order (mirrors Obsidian behavior):
        1. Relative to source file's directory
        2. From vault root
        3. Under well-known directories (for path-based links)
        4. Fallback: stem match (first match)
        """
        candidates: list[Path] = []
        if source_file:
            candidates.append(source_file.parent / link)
        candidates.append(VAULT / link)
        if "/" in link:
            for parent_dir in VAULT_DIRS:
                candidates.append(VAULT / parent_dir / link)

        for candidate in candidates:
            if candidate.suffix == "":
                candidate = candidate.with_suffix(".md")
            if candidate in self._file_set:
                return candidate

        if "/" not in link:
            matches = self._by_stem.get(link)
            if matches:
                return matches[0]

        return None


def check_wikilinks(index: WikilinkIndex | None = None) -> list[BrokenLink]:
    """Walk the vault and return all broken wikilinks."""
    if index is None:
        index = WikilinkIndex()
    broken: list[BrokenLink] = []
    for md_file in index.files:
        rel = md_file.relative_to(VAULT).as_posix()
        if any(rel.startswith(prefix) for prefix in WIKILINK_CHECK_EXCLUDE_PREFIXES):
            continue
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for link in extract_wikilinks(content):
            if link.startswith("http://") or link.startswith("https://") or "@" in link:
                continue
            if index.resolve(link, source_file=md_file) is None:
                broken.append(BrokenLink(source=md_file, link=link))
    return broken
