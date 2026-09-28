#!/usr/bin/env python3
"""Weekly memory-system audit: deterministic checks that flag, never fix.

Aggregates the existing workspace validators plus two checks with no
dedicated script, and emits one markdown report to stdout:

  1. Decision-block pruning candidates (prune-decisions.py dry run)
  2. Work repo registry drift (validate-repos.py)
  3. Stalled projects (project-status.py --stale-only)
  4. Open threads whose latest referenced date is past-due
  5. review-memory cadence (sessions since the last memory review)
  6. Stale staging files (memory/staging/*.md older than 14 days)

Designed for the weekly-review cron job; also runnable on demand:

    python scripts/workspace/memory-audit.py [--days 7]

Never modifies memory files. Always exits 0 — findings are data, not
failures, so cron logs stay clean.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, timedelta

from lib import WORKSPACE

INDEX = WORKSPACE / "memory" / "index.md"
SESSIONS_DIR = WORKSPACE / "memory" / "sessions"
REVIEWS_DIR = WORKSPACE / "memory" / "reviews"
STAGING_DIR = WORKSPACE / "memory" / "staging"
WORKSPACE_SCRIPTS = WORKSPACE / "scripts" / "workspace"

# Staging files are short-term working memory; anything older than this
# should have been promoted, archived, or deleted (see staging/README.md).
STALE_STAGING_DAYS = 14

# ---------------------------------------------------------------------------
# Date extraction (checks 4 & 5)
# ---------------------------------------------------------------------------

ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
# "Sept 8", "September 8th", "Dec 25." — month name followed by day number.
MONTH_NAME_RE = re.compile(
    r"\b(" + "|".join(_MONTHS) + r")(?:\w*)\s+(\d{1,2})(?:st|nd|rd|th)?\b",
    re.IGNORECASE,
)

# How far a month-name date may sit in the past before we roll it a year
# forward. Deadline threads reference near-past and near-future dates, so a
# ~6-month window keeps "Sept 8" in September of the right year.
WRAP_PAST_DAYS = 200
WRAP_FUTURE_DAYS = 200


def extract_dates(text: str, today: date) -> list[date]:
    """All ISO and month-name dates mentioned in text (deduped, order-kept)."""
    found: list[date] = []
    seen: set[date] = set()

    def add(d: date) -> None:
        if d not in seen:
            seen.add(d)
            found.append(d)

    for m in ISO_DATE_RE.finditer(text):
        try:
            add(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            continue

    for m in MONTH_NAME_RE.finditer(text):
        month = _MONTHS[m.group(1).lower()]
        day = int(m.group(2))
        try:
            d = date(today.year, month, day)
        except ValueError:
            continue
        # Pick the occurrence nearest to today (handles year boundaries).
        if (today - d).days > WRAP_PAST_DAYS:
            d = date(today.year + 1, month, day)
        elif (d - today).days > WRAP_FUTURE_DAYS:
            d = date(today.year - 1, month, day)
        add(d)

    return found


# ---------------------------------------------------------------------------
# Check 4: open threads with past-due dates
# ---------------------------------------------------------------------------

@dataclass
class StaleThread:
    preview: str
    latest: date
    age_days: int


def open_thread_bullets(content: str) -> list[str]:
    """Top-level bullets of the '## Open threads' section of index.md."""
    lines = content.split("\n")
    bullets: list[str] = []
    in_section = False
    current: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if in_section:
                break
            in_section = line.strip() == "## Open threads"
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                bullets.append(" ".join(current))
            current = [stripped[2:]]
        elif current and stripped:
            # Continuation line of a multi-line bullet.
            current.append(stripped)
        else:
            if current:
                bullets.append(" ".join(current))
                current = []

    if current:
        bullets.append(" ".join(current))
    return bullets


def stale_threads(content: str, today: date, stale_days: int) -> list[StaleThread]:
    """Threads whose latest referenced date is stale_days+ in the past."""
    cutoff = today - timedelta(days=stale_days)
    stale: list[StaleThread] = []
    for bullet in open_thread_bullets(content):
        dates = extract_dates(bullet, today)
        if not dates:
            continue
        latest = max(dates)
        if latest < cutoff:
            preview = re.sub(r"\s+", " ", bullet)
            if len(preview) > 120:
                preview = preview[:117] + "..."
            stale.append(StaleThread(preview, latest, (today - latest).days))
    stale.sort(key=lambda t: t.age_days, reverse=True)
    return stale


# ---------------------------------------------------------------------------
# Check 5: review cadence
# ---------------------------------------------------------------------------

@dataclass
class ReviewCadence:
    last_review: date | None
    sessions_since: int
    days_since: int | None


def _filename_date(name: str) -> date | None:
    """The ISO date embedded in a filename like 2026-07-29.md, if any."""
    m = ISO_DATE_RE.search(name)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(0))
    except ValueError:
        return None


def review_cadence(today: date) -> ReviewCadence:
    review_dates = [
        d for f in REVIEWS_DIR.glob("*.md") if (d := _filename_date(f.name))
    ]
    if not review_dates:
        return ReviewCadence(None, _count_sessions_since(None), None)
    last = max(review_dates)
    return ReviewCadence(last, _count_sessions_since(last), (today - last).days)


def _count_sessions_since(since: date | None) -> int:
    count = 0
    for f in SESSIONS_DIR.glob("*.md"):
        d = _filename_date(f.name)
        if d and (since is None or d > since):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Check 6: stale staging files
# ---------------------------------------------------------------------------

@dataclass
class StaleStagingFile:
    name: str
    file_date: date
    age_days: int


def stale_staging(today: date) -> list[StaleStagingFile]:
    """Dated staging files older than STALE_STAGING_DAYS (README.md excluded)."""
    stale: list[StaleStagingFile] = []
    if not STAGING_DIR.exists():
        return stale
    for f in STAGING_DIR.glob("*.md"):
        d = _filename_date(f.name)
        if d is None:
            continue
        age = (today - d).days
        if age > STALE_STAGING_DAYS:
            stale.append(StaleStagingFile(f.name, d, age))
    stale.sort(key=lambda s: s.age_days, reverse=True)
    return stale


# ---------------------------------------------------------------------------
# Checks 1–3: delegate to the existing scripts, keep their summary lines
# ---------------------------------------------------------------------------

def _run_script(script: str, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(WORKSPACE_SCRIPTS / script), *args],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


def prune_candidates() -> list[str]:
    """Candidate decision-block dates from prune-decisions.py dry run."""
    out = _run_script("prune-decisions.py")
    return re.findall(r"^\s+- (\d{4}-\d{2}-\d{2}) ", out, re.MULTILINE)


def repo_registry_issues() -> list[str]:
    out = _run_script("validate-repos.py")
    issues = [l.rstrip() for l in out.splitlines() if l.lstrip().startswith(("✗", "⚠"))]
    return issues


def stalled_projects(days: int) -> list[str]:
    out = _run_script("project-status.py", "--stale-only", "--days", str(days))
    rows = []
    for line in out.splitlines():
        if "*STALE*" in line:
            m = re.match(r"^(Active|Paused)\s+(.+?)\s{2,}", line)
            if m:
                rows.append(f"{m.group(2).strip()} ({m.group(1)})")
            else:
                rows.append(line.strip())
    return rows


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(days: int, today: date) -> str:
    lines: list[str] = [f"## Memory audit ({today.isoformat()})", ""]
    findings = 0

    # Check 1: pruning candidates
    cands = prune_candidates()
    if cands:
        findings += 1
        lines.append(
            f"- **Decision pruning**: {len(cands)} block(s) ready to archive "
            f"(oldest {cands[-1]}) — review, then "
            f"`python scripts/workspace/prune-decisions.py --prune`"
        )
    else:
        lines.append("- **Decision pruning**: no candidates (clean)")

    # Check 2: repo registry
    issues = repo_registry_issues()
    if issues:
        findings += 1
        lines.append(f"- **Repo registry**: {len(issues)} issue(s):")
        for i in issues:
            lines.append(f"  - {i.lstrip('✗⚠ ')}")
        lines.append("  Fix: update `memory/work-repos.md` and bump `last_verified`.")
    else:
        lines.append("- **Repo registry**: matches disk (clean)")

    # Check 3: stalled projects
    stalled = stalled_projects(days)
    if stalled:
        lines.append(
            f"- **Stalled projects** (no session in {days}d): "
            + ", ".join(stalled)
        )
    else:
        lines.append(f"- **Stalled projects**: none in the last {days} days")

    # Check 4: past-due open threads
    content = INDEX.read_text() if INDEX.exists() else ""
    threads = stale_threads(content, today, days)
    if threads:
        findings += 1
        lines.append(f"- **Open threads possibly past-due** ({len(threads)}):")
        for t in threads:
            lines.append(f"  - {t.preview} _(latest date {t.latest}, {t.age_days}d ago)_")
    else:
        lines.append("- **Open threads**: no past-due references")

    # Check 5: review cadence
    cadence = review_cadence(today)
    if cadence.last_review is None:
        findings += 1
        lines.append("- **Review cadence**: no reviews found — run `review-memory`")
    elif cadence.sessions_since > 5 or (cadence.days_since or 0) > 7:
        findings += 1
        lines.append(
            f"- **Review cadence**: last review {cadence.last_review} "
            f"({cadence.days_since}d ago, {cadence.sessions_since} sessions since) "
            "— run `review-memory`"
        )
    else:
        lines.append(
            f"- **Review cadence**: ok (last review {cadence.last_review}, "
            f"{cadence.sessions_since} sessions since)"
        )

    # Check 6: stale staging files
    staging = stale_staging(today)
    if staging:
        findings += 1
        lines.append(f"- **Stale staging files** (older than {STALE_STAGING_DAYS}d):")
        for s in staging:
            lines.append(f"  - `{s.name}` ({s.age_days}d old)")
        lines.append(
            "  Promote, archive, or delete them (`memory-promoter` skill; "
            "see `memory/staging/README.md` lifecycle)."
        )
    else:
        lines.append("- **Stale staging files**: none")

    if findings == 0:
        lines.append("")
        lines.append("✅ Nothing needs attention.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Weekly memory-system audit (flags only, never fixes)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Staleness threshold in days for projects and open threads (default: 7)",
    )
    args = parser.parse_args()

    report = build_report(days=args.days, today=date.today())
    print(report)
    sys.exit(0)


if __name__ == "__main__":
    main()
