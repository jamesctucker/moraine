#!/usr/bin/env python3
"""Structure Validator — validates workspace conventions and integrity.

Checks:
  1. All SKILL.md files have valid YAML frontmatter with required fields (name, description)
  2. Skill directory names match frontmatter `name` and follow kebab-case
  3. All PERSONA.md files follow the template structure
  4. memory/index.md references are not orphaned
  5. Artifact filenames follow NN-title.md convention
  6. No broken wikilinks in the Obsidian vault
  7. Project top notes have required frontmatter, are indexed in projects.md,
     are linked from another note, and have a reviewed date under 60 days

Usage:
  python scripts/workspace/validate.py          # validate entire workspace
  python scripts/workspace/validate.py --quiet  # only print errors
  python scripts/workspace/validate.py --skills # validate skills only
  python scripts/workspace/validate.py --vault  # validate obsidian vault only
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from lib import (
    VAULT,
    WORKSPACE,
    WikilinkIndex,
    check_wikilinks,
    extract_wikilinks,
    parse_detailed,
)

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ARTIFACT_NAME_RE = re.compile(r"^\d{2}[a-z]?-[a-z0-9-]+\.md$")
SESSION_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$")
REVIEW_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(-[a-z0-9-]+)?\.md$")

# Required frontmatter fields for PERSONA.md files.
# Kept in sync with personas/_template/PERSONA.md.
PERSONA_REQUIRED_FRONTMATTER = {"name", "role", "expertise", "style"}


class ValidationContext:
    """Collects errors and warnings from validation functions."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


# ── SKILL validation ────────────────────────────────────────────────


def validate_skills(ctx: ValidationContext) -> None:
    skills_dir = WORKSPACE / ".opencode" / "skills"
    if not skills_dir.is_dir():
        ctx.warn(f"Skills directory not found: {skills_dir}")
        return

    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        skill_dir = skill_md.parent
        dir_name = skill_dir.name

        if not SKILL_NAME_RE.match(dir_name):
            ctx.error(
                f"Skill directory name '{dir_name}' does not match "
                f"kebab-case pattern (lowercase alphanumeric, single hyphens)"
            )

        content = skill_md.read_text()
        rel = str(skill_md.relative_to(WORKSPACE))
        result = parse_detailed(content)
        if result.error:
            ctx.error(f"{rel}: {result.error.kind.name.lower()}: {result.error.detail}")
            continue
        if result.frontmatter is None:
            continue

        frontmatter = result.frontmatter
        name = frontmatter.get("name")
        description = frontmatter.get("description")

        if not name:
            ctx.error(f"SKILL.md missing required 'name' in {skill_md.relative_to(WORKSPACE)}")
        elif not SKILL_NAME_RE.match(str(name)):
            ctx.error(
                f"SKILL.md 'name' field '{name}' in {skill_md.relative_to(WORKSPACE)} does not match kebab-case pattern"
            )

        if not description:
            ctx.error(f"SKILL.md missing required 'description' in {skill_md.relative_to(WORKSPACE)}")

        if name and name != dir_name:
            ctx.error(
                f"SKILL.md 'name' '{name}' does not match directory name "
                f"'{dir_name}' in {skill_dir.relative_to(WORKSPACE)}"
            )


# ── PERSONA validation ──────────────────────────────────────────────


def validate_personas(ctx: ValidationContext) -> None:
    personas_dir = WORKSPACE / "personas"
    if not personas_dir.is_dir():
        ctx.warn(f"Personas directory not found: {personas_dir}")
        return

    for persona_dir in sorted(personas_dir.iterdir()):
        if not persona_dir.is_dir() or persona_dir.name.startswith("_"):
            continue

        persona_md = persona_dir / "PERSONA.md"
        if not persona_md.is_file():
            ctx.error(f"PERSONA.md missing in {persona_dir.relative_to(WORKSPACE)}")
            continue

        content = persona_md.read_text()
        rel = str(persona_md.relative_to(WORKSPACE))
        result = parse_detailed(content)
        if result.error:
            ctx.error(f"{rel}: {result.error.kind.name.lower()}: {result.error.detail}")
            continue
        if result.frontmatter is None:
            continue

        frontmatter = result.frontmatter
        missing_fm = PERSONA_REQUIRED_FRONTMATTER - set(frontmatter.keys())
        if missing_fm:
            ctx.error(f"PERSONA.md missing required frontmatter fields in {rel}: {', '.join(sorted(missing_fm))}")

        body = result.body
        has_content = bool(re.search(r"^#{1,3}\s", body, re.MULTILINE))
        if not has_content:
            ctx.warn(f"PERSONA.md appears empty (no content sections) in {rel}")


# ── Memory index validation ─────────────────────────────────────────


def validate_memory_index(ctx: ValidationContext) -> None:
    index_path = WORKSPACE / "memory" / "index.md"
    if not index_path.is_file():
        ctx.error(f"Memory index not found: {index_path.relative_to(WORKSPACE)}")
        return

    sessions_dir = WORKSPACE / "memory" / "sessions"
    reviews_dir = WORKSPACE / "memory" / "reviews"

    if sessions_dir.is_dir():
        for sf in sessions_dir.iterdir():
            if sf.is_file() and sf.suffix == ".md":
                if not SESSION_FILE_RE.match(sf.name):
                    ctx.warn(
                        f"Session file does not follow YYYY-MM-DD-description.md convention: memory/sessions/{sf.name}"
                    )

    if reviews_dir.is_dir():
        for rf in reviews_dir.iterdir():
            if rf.is_file() and rf.suffix == ".md":
                if not REVIEW_FILE_RE.match(rf.name):
                    ctx.warn(f"Review file does not follow YYYY-MM-DD[-slug].md convention: memory/reviews/{rf.name}")

    content = index_path.read_text()
    refs = set()
    for match in re.finditer(r"`([^`]+\.md)`", content):
        refs.add(match.group(1))

    for ref in refs:
        if "/" in ref:
            # Skip work/ references — those are separate git repos not tracked here
            if ref.startswith("work/"):
                continue
            # Skip template/pattern references (e.g. YYYY-Wnn.md)
            if "YYYY" in ref or "NN" in ref or "NNN" in ref:
                continue
            target = WORKSPACE / ref
            if not target.exists():
                ctx.warn(f"Memory index references non-existent file: {ref}")


# ── Artifact validation ─────────────────────────────────────────────


def validate_artifacts(ctx: ValidationContext) -> None:
    artifacts_dir = WORKSPACE / "artifacts"
    if not artifacts_dir.is_dir():
        return

    for af in artifacts_dir.iterdir():
        if af.is_file() and af.suffix == ".md":
            if af.name in ("README.md", "_TEMPLATE.md"):
                continue
            if not ARTIFACT_NAME_RE.match(af.name):
                ctx.error(f"Artifact filename does not follow NN-title.md convention: artifacts/{af.name}")
            else:
                content = af.read_text()
                has_toc = bool(re.search(r"^## Table of Contents\s*$", content, re.MULTILINE))
                if not has_toc:
                    ctx.error(f"Artifact missing Table of Contents section: artifacts/{af.name}")


# ── Obsidian wikilink validation ────────────────────────────────────


PROJECT_TOP_NOTE = "00 Top Note.md"
PROJECT_REQUIRED_KEYS = {"status", "priority"}
PROJECT_ACTIVE_KEYS = {"next-action"}
LIVE_PROJECT_STATUSES = {"Active", "Paused"}
STALE_REVIEW_DAYS = 60


def _review_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def validate_projects(ctx: ValidationContext) -> None:
    projects_dir = VAULT / "1 Projects"
    if not projects_dir.is_dir():
        return

    index = WikilinkIndex()
    top_notes = sorted(projects_dir.rglob(PROJECT_TOP_NOTE))

    # Inbound links per target, so a note linking to itself does not count.
    inbound: dict[Path, set[Path]] = defaultdict(set)
    for fp in index.files:
        for link in extract_wikilinks(fp.read_text(encoding="utf-8", errors="replace")):
            target = index.resolve(link, source_file=fp)
            if target:
                inbound[target].add(fp)

    # Notes linked from the projects index.
    index_file = projects_dir / "projects.md"
    indexed: set[Path] = set()
    if not index_file.exists():
        ctx.warn("wiki/1 Projects/projects.md missing")
    else:
        for link in extract_wikilinks(index_file.read_text(encoding="utf-8", errors="replace")):
            target = index.resolve(link, source_file=index_file)
            if target:
                indexed.add(target)
            elif not link.startswith("00"):
                ctx.error(f"projects.md: [[{link}]] → no matching note")

    for note in top_notes:
        rel = note.relative_to(VAULT)
        status_dir = rel.parts[1] if len(rel.parts) > 1 else ""
        is_live = status_dir in LIVE_PROJECT_STATUSES

        result = parse_detailed(note.read_text(encoding="utf-8", errors="replace"))
        if result.error:
            ctx.warn(f"wiki/{rel}: {result.error.kind.name.lower()}: {result.error.detail}")
            continue
        if result.frontmatter is None:
            ctx.warn(f"wiki/{rel}: no frontmatter")
            continue

        fm = result.frontmatter
        required = PROJECT_REQUIRED_KEYS | (PROJECT_ACTIVE_KEYS if is_live else set())
        for key in sorted(required - set(fm.keys())):
            ctx.warn(f"wiki/{rel}: missing `{key}` in frontmatter")

        # Completed notes are records, not work in progress: no review clock.
        reviewed = fm.get("last-reviewed")
        if reviewed is None:
            if is_live:
                ctx.warn(f"wiki/{rel}: no last-reviewed date")
        elif (reviewed_date := _review_date(reviewed)) is None:
            ctx.warn(f"wiki/{rel}: unparseable last-reviewed `{reviewed}`")
        elif is_live and (days := (date.today() - reviewed_date).days) > STALE_REVIEW_DAYS:
            ctx.warn(f"wiki/{rel}: last reviewed {days} days ago ({reviewed_date})")

        # projects.md itself is the index, so it is never expected to be indexed.
        if note != index_file and note not in indexed:
            ctx.warn(f"wiki/{rel}: not listed in projects.md")

        # A project with no inbound link at all is invisible in the graph.
        if not any(src != note for src in inbound.get(note, ())):
            ctx.warn(f"wiki/{rel}: not linked from any other note")


def validate_vault(ctx: ValidationContext) -> None:
    if not VAULT.is_dir():
        ctx.warn(f"Obsidian vault not found: {VAULT}")
        return

    for broken in check_wikilinks():
        rel = broken.source.relative_to(VAULT)
        ctx.warn(f"Broken wikilink in wiki/{rel}: [[{broken.link}]]")

    validate_projects(ctx)


# ── Main ─────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workspace structure and conventions.")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only print errors")
    parser.add_argument("--skills", action="store_true", help="Validate skills only")
    parser.add_argument("--personas", action="store_true", help="Validate personas only")
    parser.add_argument("--vault", action="store_true", help="Validate vault wikilinks only")
    parser.add_argument("--memory", action="store_true", help="Validate memory index only")
    parser.add_argument("--artifacts", action="store_true", help="Validate artifacts only")
    args = parser.parse_args()

    ctx = ValidationContext()

    run_all = not any([args.skills, args.personas, args.vault, args.memory, args.artifacts])

    if run_all or args.skills:
        validate_skills(ctx)
    if run_all or args.personas:
        validate_personas(ctx)
    if run_all or args.memory:
        validate_memory_index(ctx)
    if run_all or args.artifacts:
        validate_artifacts(ctx)
    if run_all or args.vault:
        validate_vault(ctx)

    for w in ctx.warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in ctx.errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if ctx.errors:
        print(f"\n{len(ctx.errors)} error(s), {len(ctx.warnings)} warning(s)", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Validation passed ({len(ctx.warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
