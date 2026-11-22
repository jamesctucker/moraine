#!/usr/bin/env python3
"""Report freshness of PARA projects by last session activity.

Parses `wiki/1 Projects/projects.md` (Active + Paused tables) and scans
`memory/sessions/` for the most recent session mentioning each project,
flagging projects with no activity in the last N days (default 7).

Usage:
    python scripts/workspace/project-status.py
    python scripts/workspace/project-status.py --days 14
    python scripts/workspace/project-status.py --stale-only
    python scripts/workspace/project-status.py --project "Auction Re-Selling"
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date

from lib import WORKSPACE

PROJECTS_MD = WORKSPACE / "wiki" / "1 Projects" / "projects.md"
SESSIONS_DIR = WORKSPACE / "memory" / "sessions"

# A session filename looks like: 2026-07-10-m3-comp-fetcher-pipeline.md
SESSION_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
# Wiki link row: | [[path|Display Name]] | priority | next action |
# The pipe inside the link is sometimes escaped as \| in projects.md, so we
# must not split the row on raw "|". Extract the display name via regex, then
# strip the whole link out before parsing priority / next-action cells.
NAME_RE = re.compile(r"\[\[[^\[\]]*\\?\|([^\[\]]+?)\]\]")

# Priority words from projects.md mapped to a sort rank.
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Project:
    name: str
    status: str  # "Active" | "Paused"
    priority: str
    next_action: str


def parse_projects(content: str) -> list[Project]:
    """Extract projects from the Active and Paused tables in projects.md."""
    projects: list[Project] = []
    current_status: str | None = None
    in_table = False

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            current_status = heading if heading in ("Active", "Paused") else None
            in_table = False
            continue

        if current_status is None:
            continue

        if stripped.startswith("|") and "Project" not in stripped and "---" not in stripped:
            in_table = True
            m = NAME_RE.search(stripped)
            if not m:
                continue
            name = m.group(1)
            # Strip the link out, then the remaining cells are priority, next action.
            rest = NAME_RE.sub("", stripped).strip().strip("|")
            cells = [c.strip() for c in rest.split("|")]
            priority = cells[0] if cells else ""
            next_action = cells[1] if len(cells) > 1 else ""
            projects.append(Project(
                name=name,
                status=current_status,
                priority=priority,
                next_action=next_action,
            ))
        elif in_table and not stripped.startswith("|"):
            # Table ended.
            in_table = False

    return projects


def _norm_tokens(name: str) -> list[str]:
    """Distinctive, suffix-stripped tokens used to match a project in sessions.

    Handles spelling drift like "Re-Selling" vs "Reseller" by splitting on
    non-letters, dropping short words, and stripping common suffixes
    ("selling" -> "sell" matches "reseller").
    """
    words = re.findall(r"[A-Za-z]+", name)
    toks: list[str] = []
    for w in words:
        w = w.lower()
        if len(w) < 4:
            continue
        w = re.sub(r"(ing|ed|s)$", "", w)
        if w not in toks:
            toks.append(w)
    return toks


def _matches(project: Project, text: str) -> bool:
    """True if the session text references the project.

    Matches on the full name (case-insensitive) OR on all normalized tokens
    appearing together (catches spelling/hyphenation drift).
    """
    if project.name.lower() in text:
        return True
    toks = _norm_tokens(project.name)
    if not toks:
        return False
    return all(t in text for t in toks)


def last_session_date(project: Project) -> date | None:
    """Return the most recent session date mentioning the project, or None."""
    best: date | None = None

    if not SESSIONS_DIR.is_dir():
        return None

    for path in SESSIONS_DIR.glob("*.md"):
        dm = SESSION_DATE_RE.match(path.name)
        if not dm:
            continue
        try:
            fdate = date.fromisoformat(dm.group(1))
        except ValueError:
            continue
        text = path.read_text(errors="ignore").lower()
        if _matches(project, text):
            if best is None or fdate > best:
                best = fdate

    return best


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report PARA project freshness by last session activity"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        metavar="N",
        help="Flag projects with no session in the last N days (default: 7)",
    )
    parser.add_argument(
        "--stale-only",
        action="store_true",
        help="Only show projects flagged as stale",
    )
    parser.add_argument(
        "--project",
        type=str,
        metavar="NAME",
        help="Filter to a single project by name (substring match)",
    )
    args = parser.parse_args()

    if not PROJECTS_MD.exists():
        print(f"error: {PROJECTS_MD} not found", file=sys.stderr)
        sys.exit(1)

    projects = parse_projects(PROJECTS_MD.read_text())
    if args.project:
        needle = args.project.lower()
        projects = [p for p in projects if needle in p.name.lower()]
        if not projects:
            print(f"No project matching '{args.project}' in Active/Paused tables.")
            sys.exit(0)

    today = date.today()
    rows: list[tuple[Project, date | None, int]] = []
    for p in projects:
        ls = last_session_date(p)
        age = (today - ls).days if ls else 9999
        rows.append((p, ls, age))

    # Sort: stale first, then by status (Active before Paused), then priority.
    rows.sort(key=lambda r: (
        0 if r[2] > args.days else 1,
        r[0].status != "Active",
        PRIORITY_RANK.get(r[0].priority.lower(), 9),
        r[0].name.lower(),
    ))

    header = f"{'Status':<7} {'Project':<34} {'Pri':<7} {'Last session':<13} {'Age':<6} Flag"
    print(header)
    print("-" * len(header))

    stale_count = 0
    for p, ls, age in rows:
        stale = age > args.days
        if args.stale_only and not stale:
            continue
        last_str = ls.isoformat() if ls else "— never —"
        age_str = f"{age}d" if age != 9999 else "n/a"
        flag = "*STALE*" if stale else ""
        if stale:
            stale_count += 1
        print(f"{p.status:<7} {p.name:<34} {p.priority:<7} {last_str:<13} {age_str:<6} {flag}")

    print()
    if stale_count:
        print(f"⚠ {stale_count} project(s) with no session in the last {args.days} days.")
    else:
        print(f"✓ All Active/Paused projects have session activity within {args.days} days.")
    print(f"  ({len(rows)} projects checked across Active + Paused)")


if __name__ == "__main__":
    main()
