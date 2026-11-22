#!/usr/bin/env python3
"""Prune acted-upon decisions from memory/index.md to memory/historical-decisions.md.

Identifies "Recent decisions" date blocks whose items are complete and
can be archived.  Completeness is judged by heuristics: past-tense verbs,
existing file references, and absence of pending/next/in-progress signals.

Usage:
    python scripts/workspace/prune-decisions.py              # dry run report
    python scripts/workspace/prune-decisions.py --prune      # archive candidates
    python scripts/workspace/prune-decisions.py --prune --before 2026-06-01
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta

from lib import WORKSPACE

INDEX = WORKSPACE / "memory" / "index.md"
HISTORICAL = WORKSPACE / "memory" / "historical-decisions.md"

# Heading that introduces a decisions block.
BLOCK_HEADING_RE = re.compile(r"^## Recent decisions \((\d{4}-\d{2}-\d{2})\)$")

# Past-tense verbs that signal a completed action.
PAST_VERBS = re.compile(
    r"\b("
    r"created|installed|built|shipped|committed|completed|migrated|"
    r"implemented|deleted|removed|consolidated|extracted|rewritten|"
    r"fixed|updated|resolved|archived|trimmed|slimmed|replaced|"
    r"moved|added|configured|verified|confirmed|published|closed|"
    r"done|finished|delivered|landed|merged|deployed|retired|"
    r"deprecated|superseded|replaced|opted|chose|decided|agreed|"
    r"kept|documented|noted|recorded|scaffolded|refactored|"
    r"hardened|reviewed|edited|organized|imported|sorted|registered"
    r")\b",
    re.IGNORECASE,
)

# Signals that a decision is still in flight.
PENDING_SIGNALS = re.compile(
    r"\b("
    r"next|pending|awaiting|in progress|to do|to-do|to be|"
    r"not yet|not started|deferred|paused|on hold|"
    r"will re-evaluate|should|needs? (to|further|more)|"
    r"remaining|phase 2|v2|future|upcoming|planned|"
    r"before|until|when"
    r")\b",
    re.IGNORECASE,
)

BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")
PAREN_PATH_RE = re.compile(r"\(([^)]+)\)")


@dataclass
class Block:
    date_str: str
    date_obj: date
    start_line: int  # 0-indexed in raw lines
    end_line: int    # exclusive
    text: str        # full block including heading
    bullets: list[str]
    completeness: float  # 0.0-1.0


def parse_blocks(content: str) -> list[Block]:
    lines = content.split("\n")
    blocks: list[Block] = []

    i = 0
    while i < len(lines):
        m = BLOCK_HEADING_RE.match(lines[i])
        if not m:
            i += 1
            continue

        date_str = m.group(1)
        start = i
        i += 1

        # Collect lines until next heading or end of file.
        while i < len(lines) and not lines[i].startswith("## "):
            i += 1

        end = i
        text = "\n".join(lines[start:end])
        bullets = _extract_bullets(lines[start:end])
        completeness = _score_completeness(bullets)

        blocks.append(Block(
            date_str=date_str,
            date_obj=date.fromisoformat(date_str),
            start_line=start,
            end_line=end,
            text=text,
            bullets=bullets,
            completeness=completeness,
        ))

    return blocks


def _extract_bullets(lines: list[str]) -> list[str]:
    """Extract bullet-point content, joining multi-line bullets."""
    bullets: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                bullets.append(" ".join(current))
            current = [stripped[2:]]
        elif current and stripped and not stripped.startswith("#"):
            # Continuation line (indented or not).
            current.append(stripped)
        else:
            if current:
                bullets.append(" ".join(current))
            current = []

    if current:
        bullets.append(" ".join(current))

    return bullets


def _score_completeness(bullets: list[str]) -> float:
    """Return 0.0 (all pending) to 1.0 (all done)."""
    if not bullets:
        return 0.5

    scores: list[float] = []
    for b in bullets:
        has_past = bool(PAST_VERBS.search(b))
        has_pending = bool(PENDING_SIGNALS.search(b))
        has_paths = bool(BACKTICK_PATH_RE.search(b) or PAREN_PATH_RE.search(b))

        if has_past and not has_pending:
            score = 0.9
        elif has_past and has_pending:
            score = 0.5
        elif has_pending and not has_past:
            score = 0.1
        elif has_paths:
            score = 0.7
        else:
            # No action verbs — likely an informational/declarative decision
            # (e.g. "X is Y", "chose A over B").  These are inherently "done."
            score = 0.7

        # Boost if referenced files actually exist.
        if has_paths:
            real = sum(
                1
                for m in BACKTICK_PATH_RE.finditer(b)
                if _path_exists(m.group(1))
            )
            if real > 0:
                score = min(1.0, score + 0.15)

        scores.append(score)

    return sum(scores) / len(scores)


def _path_exists(candidate: str) -> bool:
    """Check if a backtick-quoted string looks like a real file path that exists."""
    candidate = candidate.strip()
    if not candidate or candidate.startswith("$") or candidate.startswith("<"):
        return False
    if " " in candidate and not candidate.endswith((".md", ".py", ".ts", ".sh")):
        return False
    # Only check shortish paths (not full sentences in backticks).
    if len(candidate) > 120:
        return False
    p = WORKSPACE / candidate
    return p.exists()


def _age_days(d: date) -> int:
    return (date.today() - d).days


def report(blocks: list[Block]) -> None:
    """Print a dry-run report of all blocks and which are candidates."""
    print(f"{'Date':>12}  {'Age':>5}  {'Done':>5}  {'Bullets':>7}  Status")
    print("-" * 60)

    candidates: list[Block] = []
    keepers: list[Block] = []

    for b in blocks:
        age = _age_days(b.date_obj)
        pct = f"{b.completeness:.0%}"

        if b.completeness >= 0.60 and age > 14:
            status = "CANDIDATE"
            candidates.append(b)
        elif age > 45:
            status = "CANDIDATE (age)"
            candidates.append(b)
        else:
            status = "keep"
            keepers.append(b)

        print(
            f"{b.date_str:>12}  {age:>4}d  {pct:>5}  "
            f"{len(b.bullets):>6}b  {status}"
        )

    print()
    if candidates:
        print(f"✓ {len(candidates)} candidate blocks ready for archival")
        for b in candidates:
            print(f"  - {b.date_str} ({_age_days(b.date_obj)}d old, {b.completeness:.0%} done)")
    else:
        print("No candidate blocks found.")

    if keepers:
        print(f"  {len(keepers)} blocks kept (too recent or incomplete)")


def prune(before_date: date | None = None, dry_run: bool = True) -> None:
    """Move candidate blocks to historical-decisions.md."""
    if not INDEX.exists():
        print(f"error: {INDEX} not found", file=sys.stderr)
        sys.exit(1)

    content = INDEX.read_text()
    blocks = parse_blocks(content)

    if before_date is None:
        # Default: archive blocks older than 14 days with completeness >= 0.60
        # (matches the report() candidate threshold).
        cutoff = date.today() - timedelta(days=14)
        candidates = [
            b for b in blocks
            if b.completeness >= 0.60 and b.date_obj <= cutoff
        ]
    else:
        candidates = [
            b for b in blocks
            if b.date_obj <= before_date
        ]

    if not candidates:
        print("No blocks to archive.")
        return

    # Sort by date ascending (oldest first for the archive).
    candidates.sort(key=lambda b: b.date_obj)

    # Build the archive text.
    archive_entries: list[str] = []
    for b in candidates:
        archive_entries.append(f"## Recent decisions ({b.date_str})\n")
        for bullet in b.bullets:
            archive_entries.append(f"- {bullet}\n")
        archive_entries.append("")

    new_archive_text = "\n".join(archive_entries)

    if dry_run:
        print(f"Would archive {len(candidates)} blocks:")
        for b in candidates:
            print(f"  - {b.date_str} ({_age_days(b.date_obj)}d old, {b.completeness:.0%} done, {len(b.bullets)} bullets)")
        print()
        print("Archive text to prepend to historical-decisions.md:")
        print("---")
        print(new_archive_text[:2000])
        if len(new_archive_text) > 2000:
            print(f"\n... ({len(new_archive_text)} chars total)")
        return

    # Prepend to historical-decisions.md.
    if HISTORICAL.exists():
        historical_content = HISTORICAL.read_text()
        # Insert after the first heading + intro paragraph.
        parts = historical_content.split("\n\n", 2)
        if len(parts) >= 2:
            new_historical = parts[0] + "\n\n" + new_archive_text + "\n" + "\n\n".join(parts[1:])
        else:
            new_historical = historical_content + "\n" + new_archive_text
    else:
        new_historical = (
            "# Historical Decisions\n\n"
            "Archived \"Recent decisions\" entries from `memory/index.md`.\n\n"
            + new_archive_text
        )

    HISTORICAL.write_text(new_historical.strip() + "\n")

    # Remove archived blocks from index.
    lines = content.split("\n")
    # Build set of line indices to remove.
    remove_indices: set[int] = set()
    for b in candidates:
        for line_idx in range(b.start_line, b.end_line):
            remove_indices.add(line_idx)

    # Also remove trailing blank lines after removed blocks.
    new_lines: list[str] = []
    skip_blank = False
    for idx, line in enumerate(lines):
        if idx in remove_indices:
            skip_blank = True
            continue
        if skip_blank and line.strip() == "":
            continue
        skip_blank = False
        new_lines.append(line)

    INDEX.write_text("\n".join(new_lines) + "\n")

    print(f"Archived {len(candidates)} blocks ({sum(len(b.bullets) for b in candidates)} decisions):")
    for b in candidates:
        print(f"  - {b.date_str}")
    print(f"Updated {INDEX.name} ({len(lines) - len(new_lines)} lines removed)")
    print(f"Updated {HISTORICAL.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prune acted-upon decisions from memory/index.md"
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Archive candidate blocks (default: dry-run report only)",
    )
    parser.add_argument(
        "--before",
        type=str,
        metavar="DATE",
        help="Archive blocks on or before this date (YYYY-MM-DD). "
             "Default: 30-day cutoff with completeness >= 0.75.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Archive regardless of completeness score (use with --before)",
    )
    args = parser.parse_args()

    if not INDEX.exists():
        print(f"error: {INDEX} not found", file=sys.stderr)
        sys.exit(1)

    content = INDEX.read_text()
    blocks = parse_blocks(content)

    if not blocks:
        print("No Recent decisions blocks found.")
        return

    if not args.prune:
        report(blocks)
        print("\nRun with --prune to archive candidates.")
        print("Use --before DATE to set a custom cutoff.")
        return

    before_date = date.fromisoformat(args.before) if args.before else None
    if args.force and args.before:
        before_date = date.fromisoformat(args.before)

    # If --force, override completeness: move everything before the date.
    if args.force and args.before:
        candidates = [b for b in blocks if b.date_obj <= date.fromisoformat(args.before)]
        # Override their completeness so prune() picks them up.
        for b in candidates:
            b.completeness = 1.0

    prune(before_date=before_date, dry_run=False)


if __name__ == "__main__":
    main()
