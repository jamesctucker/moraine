#!/usr/bin/env python3
"""Memory Promoter — scans memory/staging/ and promotes recurring topics.

An entry referenced across 3+ distinct staging days is a candidate for
promotion to a wiki project note or a session summary.

Usage:
  python scripts/workspace/memory-promoter.py              # full scan + report
  python scripts/workspace/memory-promoter.py --promote    # promote + report
  python scripts/workspace/memory-promoter.py --dry-run    # report only (default)
"""

import argparse
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

# The script lives in the reflection pack; the core library it imports
# sits three levels up in scripts/workspace.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "workspace"))

from lib import WORKSPACE, extract_wikilinks  # noqa: E402

STAGING_DIR = WORKSPACE / "memory" / "staging"
SESSIONS_DIR = WORKSPACE / "memory" / "sessions"
PROJECTS_DIR = WORKSPACE / "wiki" / "1 Projects"

SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)
PROJECT_REF_RE = re.compile(r"(?i)\b(project|initiative|workstream)\s*[:;]\s*(.+?)(?:[.\n]|$)")
BACKLINK_RE = re.compile(r"(?i)\b(see also|refers?\s+to|mentioned?\s+in|related to)\s*[:;]\s*(.+?)(?:[.\n]|$)")
COMMON_WORDS = {
    "overview", "introduction", "background", "context", "notes",
    "summary", "status", "next steps", "action items", "decisions",
    "goals", "risks", "discussion", "links", "resources", "todos",
}


def is_staging_file(path: Path) -> bool:
    name = path.name
    return (
        path.suffix == ".md"
        and name != "README.md"
        and not name.startswith("health-check")
        and not name.startswith("promotion-candidates")
    )


def extract_topics(content: str) -> list[str]:
    topics: list[str] = []
    headings = SECTION_RE.findall(content)
    for h in headings:
        h = h.strip()
        lower = h.lower()
        if lower not in COMMON_WORDS and len(h) > 3:
            topics.append(h)
    wikilinks = extract_wikilinks(content)
    for wl in wikilinks:
        stem = Path(wl).stem.replace("-", " ").replace("_", " ")
        if len(stem) > 3:
            topics.append(stem)
    for match in PROJECT_REF_RE.finditer(content):
        t = match.group(2).strip()
        if len(t) > 3:
            topics.append(t)
    for match in BACKLINK_RE.finditer(content):
        t = match.group(2).strip()
        if len(t) > 3:
            topics.append(t)
    return topics


def normalize(topic: str) -> str:
    return re.sub(r"\s+", " ", topic).strip().lower()


def dir_slug(topic: str) -> str:
    """Return a bounded slug, rejecting paths instead of renaming them."""
    if "/" in topic or "\\" in topic or ".." in topic:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return "-".join(slug.split("-")[:6])


def scan_staging() -> Counter:
    counter: Counter = Counter()
    if not STAGING_DIR.is_dir():
        return counter

    seen_topics: dict[str, set[str]] = {}

    for f in sorted(STAGING_DIR.iterdir()):
        if not is_staging_file(f):
            continue
        content = f.read_text()
        topics = extract_topics(content)
        normalized = [normalize(t) for t in topics]
        unique_topics = set(normalized)
        for t in unique_topics:
            if t not in seen_topics:
                seen_topics[t] = set()
            seen_topics[t].add(f.stem)

    for topic, dates in seen_topics.items():
        if len(dates) >= 3:
            counter[topic] = len(dates)

    return counter


def find_original_forms(topics: dict[str, int]) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    if not STAGING_DIR.is_dir():
        return result

    for f in sorted(STAGING_DIR.iterdir()):
        if not is_staging_file(f):
            continue
        content = f.read_text()
        candidates = extract_topics(content)
        for c in candidates:
            norm = normalize(c)
            if norm in topics:
                if norm not in result:
                    result[norm] = (topics[norm], c)
    return result


def already_promoted(topic_normalized: str) -> bool:
    dir_name = dir_slug(topic_normalized)
    if not dir_name:
        return False
    if PROJECTS_DIR.is_dir():
        for pdir in PROJECTS_DIR.iterdir():
            if pdir.is_dir() and dir_name in dir_slug(pdir.name):
                return True
    if SESSIONS_DIR.is_dir():
        for sf in SESSIONS_DIR.iterdir():
            if sf.suffix == ".md" and dir_name in dir_slug(sf.stem):
                return True
    return False


def write_report(candidates: dict[str, tuple[int, str]], dry_run: bool) -> Path:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"# Promotion Candidates — {today}",
        "",
        f"**Run at:** {timestamp}",
        f"**Mode:** {'dry-run' if dry_run else 'promote'}",
        f"**Candidates found:** {len(candidates)}",
        "",
        "Entries referenced across 3+ distinct staging days are listed below.",
        "",
        "| Topic | Mentions (distinct days) | Already promoted? | Sample form |",
        "|-------|-------------------------|-------------------|-------------|",
    ]

    promoted_count = 0
    for norm, (count, sample) in sorted(candidates.items(), key=lambda x: -x[1][0]):
        promoted = already_promoted(norm)
        if promoted:
            promoted_count += 1
        lines.append(f"| {sample} | {count} | {'Yes' if promoted else 'No'} | {norm} |")

    lines.append("")
    lines.append(f"**Summary:** {len(candidates)} candidate(s), {promoted_count} already promoted.")

    report_path = STAGING_DIR / f"promotion-candidates-{today}.md"
    report_path.write_text("\n".join(lines) + "\n")
    print(f"Report: {report_path.relative_to(WORKSPACE)}")
    return report_path


PROJECTS_INDEX_TEMPLATE = """# Projects

<!-- Add one row per project, in the section matching its status. Link to the project's top note. -->

## Active

| Project | Status | Priority | Next Action |
|---------|--------|----------|-------------|
"""


def index_row(dir_name: str, title: str) -> str:
    """One projects.md row linking the promoted note (Obsidian table-escaped pipe)."""
    # Square brackets would break wikilink parsing in both Obsidian and the
    # workspace's own link regex; strip them from the display alias.
    display = title.replace("[", "").replace("]", "").replace("|", r"\|")
    return f"| [[{dir_name}/00 Top Note\\|{display}]] | Active | Medium | Define scope and refine from staging notes |"


def add_to_projects_index(dir_name: str, title: str) -> None:
    """List the promoted note in projects.md so it is indexed and linked."""
    index_path = PROJECTS_DIR / "projects.md"
    row = index_row(dir_name, title)
    if not index_path.exists():
        index_path.write_text(PROJECTS_INDEX_TEMPLATE + row + "\n")
        return

    lines = index_path.read_text().splitlines()
    active = next((i for i, line in enumerate(lines) if line.strip() == "## Active"), None)
    if active is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["## Active", "", "| Project | Status | Priority | Next Action |",
                      "|---------|--------|----------|-------------|", row])
        index_path.write_text("\n".join(lines) + "\n")
        return

    # Insert after the last table row of the Active section; if the section
    # has no table at all, create one under the heading.
    insert_at = active + 1
    saw_table = False
    for i in range(active + 1, len(lines)):
        if lines[i].startswith("## "):
            break
        if lines[i].startswith("|"):
            insert_at = i + 1
            saw_table = True
    if saw_table:
        lines.insert(insert_at, row)
    else:
        lines[insert_at:insert_at] = [
            "",
            "| Project | Status | Priority | Next Action |",
            "|---------|--------|----------|-------------|",
            row,
        ]
    index_path.write_text("\n".join(lines) + "\n")


def promote_candidates(candidates: dict[str, tuple[int, str]]) -> list[Path]:
    created: list[Path] = []
    for norm, (count, sample) in sorted(candidates.items(), key=lambda x: -x[1][0]):
        if already_promoted(norm):
            continue
        dir_name = dir_slug(norm)
        if not dir_name:
            continue
        # Validate the destination before creating anything so a rejected
        # topic can never leave a half-written promotion behind.
        target_dir = PROJECTS_DIR / dir_name
        if not target_dir.resolve().is_relative_to(PROJECTS_DIR.resolve()):
            continue
        note_path = target_dir / "00 Top Note.md"
        rel = note_path.relative_to(WORKSPACE)
        next_action = "Define scope and refine from staging notes"
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        note_content = (
            f"---\nstatus: active\npriority: medium\n"
            f"tags: [auto-promoted]\n"
            f"created: {today}\n"
            f"last-reviewed: {today}\n"
            f"next-action: {next_action}\n"
            f"---\n\n## Overview\n\n"
            f"Auto-promoted from staging. Referenced {count} times across staging.\n\n"
            f"## Next Action\n\n{next_action}.\n"
        )
        new_dir = not target_dir.exists()
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            with note_path.open("x", encoding="utf-8") as f:
                f.write(note_content)
        except FileExistsError:
            continue
        except OSError as e:
            # Undo the directory so a failed write leaves no partial state.
            if new_dir:
                target_dir.rmdir()
            print(f"  Skipped {rel}: {e}")
            continue
        add_to_projects_index(dir_name, sample)
        created.append(note_path)
        print(f"  Promoted: {rel} (referenced {count}x)")
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote recurring staging entries to wiki/sessions.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--promote", action="store_true", help="Auto-promote candidates")
    group.add_argument("--dry-run", action="store_true", help="Report only (default)")
    parser.set_defaults(dry_run=True)
    args = parser.parse_args()

    print("=== Memory Promoter ===\n")

    candidates = scan_staging()
    if not candidates:
        print("No promotion candidates found.")
        report_path = STAGING_DIR / f"promotion-candidates-{datetime.now(UTC).strftime('%Y-%m-%d')}.md"
        report_path.write_text(f"# Promotion Candidates — {datetime.now(UTC).strftime('%Y-%m-%d')}\n\nNo candidates.\n")
        print(f"Report: {report_path.relative_to(WORKSPACE)}")
        return 0

    enriched = find_original_forms(candidates)
    write_report(enriched, dry_run=not args.promote)

    if args.promote:
        print("\nPromoting candidates...")
        created = promote_candidates(enriched)
        if created:
            print(f"\nCreated {len(created)} wiki project note(s).")
        else:
            print("Nothing new to promote (all candidates already exist).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
