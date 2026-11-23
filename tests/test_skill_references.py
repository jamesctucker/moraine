"""Static checks for bundled skill dependencies and local links."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
# Pack skills are scanned where they live: the links in .agents/skills are
# untracked, so a fresh clone has only the core folders there.
SKILL_ROOTS = (ROOT / ".agents" / "skills", *sorted((ROOT / "packs").glob("*/skills")))
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


def skill_markdown() -> list[Path]:
    return sorted(md for root in SKILL_ROOTS for md in root.rglob("*.md"))


def test_skill_markdown_has_no_unshipped_dependencies():
    offenders = []
    for document in skill_markdown():
        text = document.read_text()
        offenders.extend(f"{document.relative_to(ROOT)}: {token}" for token in UNSHIPPED_REFERENCES if token in text)

    assert not offenders, "Unshipped skill references:\n" + "\n".join(offenders)


def test_skill_relative_markdown_links_resolve():
    broken = []
    for document in skill_markdown():
        for target in LINK.findall(document.read_text()):
            if not target or target.startswith(("#", "/", "mailto:")) or "://" in target:
                continue
            relative = unquote(target.split("#", 1)[0])
            if relative and not (document.parent / relative).resolve().exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")

    assert not broken, "Broken skill links:\n" + "\n".join(broken)


# ── The core/pack boundary ───────────────────────────────────────────
#
# Core files — real folders in .agents/skills, scripts/workspace/*.py,
# scripts/moraine, and the root AGENTS.md — reference no pack's skill or
# script unless the line says the pack is enabled ("If the `quality` pack
# is enabled" — the line must contain "`<pack>` pack"). The `local` pack
# is always enabled, so its names are always allowed.
#
# Matcher grammar, tuned against the real tree (bare pack names and
# common-word skill ids otherwise give false positives):
#   - skill ids containing a hyphen match as tokens anywhere on a line
#   - single-word ids only match in explicit skill context:
#     `see \`X\``, `**\`X\`**`, `\`X\` skill`, `Skill tool with "X"`,
#     `/skills/X`
#   - pack names match only in `packs/<name>/` path form
#   - script names are the file and directory basenames under packs/<p>/
#     (excluding skills/, tests/, pack.yaml, AGENTS.md) and match as tokens
#
# Known exemptions, documented rather than worked around:
#   - `JOB_RUNNER_PACK = "automation"` in sync.py — the job-runner switch
#     is core by design (and never appears in packs/automation/ form).
#   - agent-eval.py loads `eval.py` from enabled packs by convention; the
#     core harness names no pack.
EXEMPT_REFERENCES = {
    ("scripts/workspace/agent-eval.py", "eval.py"),
}

LOCAL_PACK = "local"
PACKS_DIR = ROOT / "packs"
CORE_FILES = [
    *sorted(p for p in (ROOT / ".agents" / "skills").iterdir() if not p.is_symlink()),
    *sorted((ROOT / "scripts" / "workspace").glob("*.py")),
    ROOT / "scripts" / "moraine",
    ROOT / "AGENTS.md",
]

# Single-word skill ids need explicit skill context to count as a reference.
SKILL_CONTEXT = [
    re.compile(r"see `([^`]+)`"),
    re.compile(r"\*\*`([^`]+)`\*\*"),
    re.compile(r"`([^`]+)` skill"),
    re.compile(r'Skill tool with "([^"]+)"'),
    re.compile(r"/skills/([A-Za-z0-9_-]+)"),
]


def _token(line: str, name: str) -> bool:
    """`name` appears as a whole word; hyphens and dots belong to it."""
    return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", line) is not None


def _pack_names() -> set[str]:
    return {p.name for p in PACKS_DIR.iterdir() if p.is_dir()}


def _pack_skills() -> dict[str, str]:
    """Skill id -> owning pack, for every shipped pack skill."""
    return {
        skill.name: pack.name
        for pack in sorted(PACKS_DIR.iterdir())
        if pack.is_dir()
        for skill in (pack / "skills").glob("*")
    }


def _pack_scripts() -> dict[str, str]:
    """File basename -> owning pack, outside skills/ and tests/.

    Directories are not collected: `scripts`, `jobs`, `docs`, and `rules`
    are common words that name core folders too.
    """
    found: dict[str, str] = {}
    for pack in sorted(PACKS_DIR.iterdir()):
        if not pack.is_dir():
            continue
        for path in pack.rglob("*"):
            if not path.is_file() or path in (pack / "pack.yaml", pack / "AGENTS.md"):
                continue
            relative = path.relative_to(pack)
            if relative.parts[0] in ("skills", "tests"):
                continue
            found.setdefault(path.name, pack.name)
    return found


def _conditional(line: str, pack: str) -> bool:
    return f"`{pack}` pack" in line


def test_core_names_no_pack_skill_or_script_unless_conditional():
    pack_skills = _pack_skills()
    pack_scripts = _pack_scripts()
    hyphenated = {sid: pack for sid, pack in pack_skills.items() if "-" in sid}
    single_word = {sid: pack for sid, pack in pack_skills.items() if "-" not in sid}

    offenders = []
    for path in CORE_FILES:
        if path.is_file():
            documents = [path]
        else:
            documents = sorted(p for p in path.rglob("*") if p.is_file())
        for document in documents:
            for lineno, line in enumerate(
                document.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                where = f"{document.relative_to(ROOT)}:{lineno}"

                for skill_id, pack in hyphenated.items():
                    if pack != LOCAL_PACK and _token(line, skill_id) and not _conditional(line, pack):
                        offenders.append(f"{where}: skill '{skill_id}' ({pack} pack) without a conditional")

                context_ids = {m for pattern in SKILL_CONTEXT for m in pattern.findall(line)}
                for skill_id, pack in single_word.items():
                    if pack != LOCAL_PACK and skill_id in context_ids and not _conditional(line, pack):
                        offenders.append(f"{where}: skill '{skill_id}' ({pack} pack) without a conditional")

                for pack in _pack_names():
                    if pack != LOCAL_PACK and f"packs/{pack}/" in line and not _conditional(line, pack):
                        offenders.append(f"{where}: pack path 'packs/{pack}/' without a conditional")

                for name, pack in pack_scripts.items():
                    if pack == LOCAL_PACK or (str(document.relative_to(ROOT)), name) in EXEMPT_REFERENCES:
                        continue
                    if _token(line, name) and not _conditional(line, pack):
                        offenders.append(f"{where}: script '{name}' ({pack} pack) without a conditional")

    assert not offenders, "Core references pack content without saying the pack is enabled:\n" + "\n".join(offenders)
