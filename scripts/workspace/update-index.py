#!/usr/bin/env python3
"""Memory Index Auto-Updater — regenerates memory/index.md from session and review files.

Reads memory/sessions/*.md and memory/reviews/*.md and updates memory/index.md
with current projects, open threads, recent decisions, skills, and personas.

Preserves manually-maintained sections (Active projects, Open threads) and any
unrecognized top-level content that doesn't match known section headings.

Usage:
  python scripts/workspace/update-index            # regenerate memory/index.md
  python scripts/workspace/update-index --dry-run  # print what would change without writing
"""
import argparse
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from lib import WORKSPACE, parse

MEMORY_DIR = WORKSPACE / "memory"
SESSIONS_DIR = MEMORY_DIR / "sessions"
REVIEWS_DIR = MEMORY_DIR / "reviews"
INDEX_PATH = MEMORY_DIR / "index.md"
SKILLS_DIR = WORKSPACE / ".opencode" / "skills"
PERSONAS_DIR = WORKSPACE / "personas"

KNOWN_SECTIONS = {
    "Active projects",
    "Open threads",
    "Recent decisions",
    "Skills active",
    "Personas active",
}


def gather_skills() -> list[tuple[str, str]]:
    if not SKILLS_DIR.is_dir():
        return []
    skills = []
    # Skills live at .opencode/skills/<category>/<name>/SKILL.md, but the
    # flat .opencode/skills/<name>/SKILL.md layout is honoured too.
    for md in sorted(SKILLS_DIR.rglob("SKILL.md")):
        content = md.read_text()
        fm, _body = parse(content)
        if fm is not None:
            name = fm.get("name", md.parent.name)
            desc = fm.get("description", "")
            skills.append((name, desc))
    return skills


def gather_personas() -> list[tuple[str, str]]:
    if not PERSONAS_DIR.is_dir():
        return []
    personas = []
    for d in sorted(PERSONAS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("_"):
            md = d / "PERSONA.md"
            if md.is_file():
                content = md.read_text()
                fm, _body = parse(content)
                if fm is not None:
                    name = fm.get("name", d.name)
                    role = fm.get("role", "")
                    personas.append((name, role))
    return personas


def gather_sessions() -> list[Path]:
    if not SESSIONS_DIR.is_dir():
        return []
    return sorted(
        [f for f in SESSIONS_DIR.iterdir() if f.is_file() and f.suffix == ".md"],
        reverse=True,
    )


def gather_reviews() -> list[Path]:
    if not REVIEWS_DIR.is_dir():
        return []
    return sorted(
        [f for f in REVIEWS_DIR.iterdir() if f.is_file() and f.suffix == ".md"],
        reverse=True,
    )


def extract_section(content: str, heading: str, max_level: int = 2, prefix_match: bool = False) -> str:
    """Extract the body of a markdown section by heading.

    If prefix_match is True, matches headings that *start with* the given
    heading text (e.g. "Recent decisions" matches "Recent decisions (2026-05-12)").
    """
    heading_re = "#" * max_level
    if prefix_match:
        pattern = rf"^{heading_re}\s+{re.escape(heading)}[^\n]*\n(.*?)(?=^{heading_re}\s|\Z)"
    else:
        pattern = rf"^{heading_re}\s+{re.escape(heading)}\s*$\n(.*?)(?=^{heading_re}\s|\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    if max_level < 4:
        return extract_section(content, heading, max_level + 1, prefix_match=prefix_match)
    return ""


def extract_all_dated_sections(content: str, heading_prefix: str, max_level: int = 2) -> list[tuple[str, str]]:
    """Extract all sections whose heading starts with heading_prefix.

    Returns a list of (full_heading, section_body) tuples.
    """
    heading_re = "#" * max_level
    pattern = rf"^({heading_re}\s+{re.escape(heading_prefix)}[^\n]*)\n(.*?)(?=^{heading_re}\s|\Z)"
    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
    if matches:
        return [(h.strip(), b.strip()) for h, b in matches]
    if max_level < 4:
        return extract_all_dated_sections(content, heading_prefix, max_level + 1)
    return []


def extract_decisions_from_sessions(sessions: list[Path]) -> dict[str, list[str]]:
    decisions: dict[str, list[str]] = {}
    for sf in sessions[:10]:
        content = sf.read_text()
        for heading in ["Decisions", "Recent decisions", "Key decisions"]:
            section = extract_section(content, heading)
            if section:
                date_str = sf.stem[:10]
                if date_str not in decisions:
                    decisions[date_str] = []
                for line in section.strip().split("\n"):
                    cleaned = re.sub(r"^[-\s]+", "", line).strip()
                    if cleaned:
                        decisions[date_str].append(cleaned)
    return decisions


def preserve_section_from_existing(heading: str) -> str | None:
    if not INDEX_PATH.is_file():
        return None
    current = INDEX_PATH.read_text()
    section = extract_section(current, heading)
    if section:
        return section
    return None


def _is_known_heading(heading_text: str) -> bool:
    """Check if a heading matches a known section (exact or prefix match for dated sections)."""
    if heading_text in KNOWN_SECTIONS:
        return True
    for known in KNOWN_SECTIONS:
        if heading_text.startswith(known):
            return True
    return False


def preserve_unrecognized_content() -> str:
    if not INDEX_PATH.is_file():
        return ""
    content = INDEX_PATH.read_text()
    lines = content.split("\n")
    unrecognized: list[str] = []
    current_section: list[str] = []
    in_known = False

    for line in lines:
        heading_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading_match:
            if current_section and not in_known:
                unrecognized.extend(current_section)
            current_section = []
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            # Skip the document title (H1) and any known/dated sections
            in_known = (level == 1) or _is_known_heading(heading_text)
        current_section.append(line)

    if current_section and not in_known:
        unrecognized.extend(current_section)

    return "\n".join(unrecognized).strip()


def build_index(
    sessions: list[Path],
    reviews: list[Path],
    skills: list[tuple[str, str]],
    personas: list[tuple[str, str]],
) -> str:
    lines: list[str] = []
    lines.append("# Memory Index")
    lines.append("")

    preserved = preserve_unrecognized_content()

    lines.append("## Active projects")
    lines.append("")
    projects_section = preserve_section_from_existing("Active projects")
    if projects_section:
        lines.append(projects_section)
        lines.append("")
    else:
        lines.append("_No projects tracked yet._")
        lines.append("")

    lines.append("## Open threads")
    lines.append("")
    threads_section = preserve_section_from_existing("Open threads")
    if threads_section:
        lines.append(threads_section)
        lines.append("")
    else:
        lines.append("_No open threads._")
        lines.append("")

    # Merge decisions: extract from sessions AND preserve existing dated
    # sections from the current index. Same-date entries from both sources
    # are combined and deduplicated, so manually-added decisions survive
    # regeneration even when a session covers the same date.
    decisions = extract_decisions_from_sessions(sessions)
    if INDEX_PATH.is_file():
        existing_content = INDEX_PATH.read_text()
        existing_dated = extract_all_dated_sections(existing_content, "Recent decisions")
        for heading, body in existing_dated:
            date_match = re.search(r"\((\d{4}-\d{2}-\d{2})\)", heading)
            if date_match:
                date_str = date_match.group(1)
                merged = decisions.setdefault(date_str, [])
                for line in body.strip().split("\n"):
                    cleaned = re.sub(r"^[-\s]+", "", line).strip()
                    if cleaned and cleaned not in merged:
                        merged.append(cleaned)

    if decisions:
        for date_str in sorted(decisions.keys(), reverse=True):
            lines.append(f"## Recent decisions ({date_str})")
            lines.append("")
            for d in decisions[date_str]:
                lines.append(f"- {d}")
            lines.append("")

    # Reviews summary
    if reviews:
        lines.append("## Recent reviews")
        lines.append("")
        for review_path in reviews[:5]:
            date_str = review_path.stem
            lines.append(f"- `memory/reviews/{review_path.name}` ({date_str})")
        lines.append("")

    lines.append("## Skills active")
    lines.append("")
    if skills:
        for name, desc in skills:
            lines.append(f"- `{name}` — {desc}")
        lines.append("")
    else:
        lines.append("_No skills._")
        lines.append("")

    lines.append("## Personas active")
    lines.append("")
    if personas:
        for name, role in personas:
            lines.append(f"- `{name}` — {role}")
        lines.append("")
    else:
        lines.append("_No personas._")
        lines.append("")

    if preserved:
        lines.append(preserved)
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate memory/index.md from session and review files."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing",
    )
    args = parser.parse_args()

    sessions = gather_sessions()
    reviews = gather_reviews()
    skills = gather_skills()
    personas = gather_personas()

    new_index = build_index(sessions, reviews, skills, personas)

    if args.dry_run:
        print(new_index)
        return 0

    backup = None
    if INDEX_PATH.is_file():
        backup = INDEX_PATH.read_text()

    # Atomic write: write to temp file in same directory, then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=str(MEMORY_DIR), suffix=".md", prefix=".index-"
    )
    closed = False
    try:
        os.write(fd, new_index.encode())
        os.close(fd)
        closed = True
        os.replace(tmp_path, str(INDEX_PATH))
    except BaseException:
        if not closed:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    if backup is not None:
        for h in KNOWN_SECTIONS:
            old_sec = extract_section(backup, h, prefix_match=True)
            new_sec = extract_section(new_index, h, prefix_match=True)
            if old_sec and not new_sec:
                print(f"WARNING: Section '{h}' was removed from the index", file=sys.stderr)

    print(f"Updated {INDEX_PATH.relative_to(WORKSPACE)}")
    print(f"  {len(sessions)} sessions, {len(reviews)} reviews")
    print(f"  {len(skills)} skills, {len(personas)} personas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
