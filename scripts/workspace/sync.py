"""moraine sync: make the workspace match moraine.yaml.

Four pieces of state are derived from the manifests and nothing else:

1. one symlink per enabled pack skill, in .agents/skills/
2. the `# moraine:managed` block in .git/info/exclude, listing those symlinks
3. the `mcp.servers` block of each harness's MCP config
4. ~/.moraine/cron/enabled.json, the job files the cron runner installs

Sync never installs anything and never touches a real skill folder. Running
it twice changes nothing the second time.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from lib import WORKSPACE, skill_dirs
from manifest import (
    Manifest,
    Pack,
    enabled_packs,
    install_hint,
    load_manifests,
    local_pack,
    merged_mcp,
    missing_prereqs,
    pack_skills,
)

SKILLS_DIR = ".agents/skills"
OPENCODE_CONFIG = ".opencode/opencode.json"
EXCLUDE_PATH = ".git/info/exclude"
EXCLUDE_BEGIN = "# moraine:managed"
EXCLUDE_END = "# moraine:managed end"
# Job files from every pack are inert without a runner, so the pack that
# ships one is the switch for all of them.
JOB_RUNNER_PACK = "automation"


class SyncError(Exception):
    """The manifests are valid but cannot be realised as written."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Change:
    """One edit sync makes. `text` is the link target, or the file content."""

    kind: str  # link | remove | write
    path: Path
    text: str = ""
    detail: str = ""  # what happened, for the report


@dataclass
class SyncPlan:
    changes: list[Change]  # pending when planned, done once applied
    notes: list[str]  # missing prerequisites, jobs skipped
    packs: list[str]  # one summary line per enabled pack


def default_cron_state() -> Path:
    return Path.home() / ".moraine" / "cron"


# ── Plan and apply ──────────────────────────────────────────────────


def plan(workspace: Path = WORKSPACE, cron_state: Path | None = None) -> SyncPlan:
    """Everything that differs from moraine.yaml, without touching the disk."""
    manifest, packs = load_manifests(workspace)
    enabled = enabled_packs(manifest.packs, packs)
    targets = link_targets(workspace, enabled)
    changes = skill_changes(workspace, targets)
    if exclude := exclude_change(workspace, sorted(targets)):
        changes.append(exclude)
    servers = merged_mcp(manifest, enabled)[0]
    changes += mcp_change(workspace, manifest, servers)
    job_edits, skipped = job_change(workspace, enabled, cron_state or default_cron_state())
    notes = prereq_notes(enabled)
    if servers and not manifest.harnesses:
        notes.append("no harness is listed in moraine.yaml, so the MCP servers were written nowhere; add the one you run")
    if skipped:
        notes.append(skipped)
    return SyncPlan(changes + job_edits, notes, [pack_line(pack) for pack in enabled.values()])


def run(workspace: Path = WORKSPACE, cron_state: Path | None = None, dry_run: bool = False) -> SyncPlan:
    """Bring the workspace in line with moraine.yaml and return what was done."""
    result = plan(workspace, cron_state)
    if not dry_run:
        for change in result.changes:
            APPLY[change.kind](change)
    return result


def _link(change: Change) -> None:
    change.path.parent.mkdir(parents=True, exist_ok=True)
    change.path.symlink_to(change.text)


def _remove(change: Change) -> None:
    change.path.unlink()


def _write(change: Change) -> None:
    # Same-directory temporary, then rename: a reader never sees a half file.
    change.path.parent.mkdir(parents=True, exist_ok=True)
    temporary = change.path.with_name(change.path.name + ".tmp")
    temporary.write_text(change.text)
    temporary.replace(change.path)


APPLY: dict[str, Callable[[Change], None]] = {"link": _link, "remove": _remove, "write": _write}


# ── 1. Skills ───────────────────────────────────────────────────────


def link_targets(workspace: Path, enabled: dict[str, Pack]) -> dict[str, Path]:
    """Skill ID -> pack folder to link. An ID claimed twice is an error naming both."""
    core = {skill.name: skill for skill in skill_dirs(workspace / SKILLS_DIR) if not skill.is_symlink()}
    targets: dict[str, Path] = {}
    problems: list[str] = []
    packs = sorted((local_pack(workspace), *enabled.values()), key=lambda pack: pack.name)
    for pack in packs:
        for skill in pack_skills(pack):
            other = targets.get(skill.name, core.get(skill.name))
            if other is None:
                targets[skill.name] = skill
            else:
                problems.append(
                    f"skill '{skill.name}' exists in both {_shown(workspace, other)} and "
                    f"{_shown(workspace, skill)}; rename one or disable a pack"
                )
    if problems:
        raise SyncError(problems)
    return targets


def skill_changes(workspace: Path, targets: dict[str, Path]) -> list[Change]:
    """Links to create or repoint, and managed links whose skill is no longer enabled."""
    skills_dir = workspace / SKILLS_DIR
    present = {entry.name: entry for entry in skills_dir.iterdir()} if skills_dir.is_dir() else {}
    changes = [
        change
        for skill_id, target in sorted(targets.items())
        for change in _link_changes(workspace, skills_dir, present.get(skill_id), target)
    ]
    stale = [
        Change("remove", entry, detail=f"remove stale {SKILLS_DIR}/{skill_id}")
        for skill_id, entry in sorted(present.items())
        if skill_id not in targets and _is_managed(entry, workspace)
    ]
    return changes + stale


def _link_changes(workspace: Path, skills_dir: Path, entry: Path | None, target: Path) -> list[Change]:
    """The edits that make `target.name` under `skills_dir` a link to `target`."""
    skill_id = target.name
    path = skills_dir / skill_id
    wanted = os.path.relpath(target, skills_dir)
    shown = f"{SKILLS_DIR}/{skill_id}"
    if entry is None:
        return [Change("link", path, wanted, f"link {shown}")]
    if entry.is_symlink() and os.readlink(entry) == wanted:
        return []
    if not _is_managed(entry, workspace):
        raise SyncError(
            [f"{shown} already exists and sync does not own it; remove it, or rename {_shown(workspace, target)}"]
        )
    return [Change("remove", path, detail=f"remove stale {shown}"), Change("link", path, wanted, f"link {shown}")]


def _is_managed(entry: Path, workspace: Path) -> bool:
    """Whether sync owns `entry`: a link, or a link checked out as text, into packs/."""
    if entry.is_symlink():
        target = os.readlink(entry)
    elif entry.is_file():
        target = entry.read_text().strip()  # core.symlinks=false stores a link as one line
    else:
        return False
    try:
        (entry.parent / target).resolve().relative_to((workspace / "packs").resolve())
    except ValueError:
        return False
    return True


def exclude_change(workspace: Path, skill_ids: list[str]) -> Change | None:
    """Rewrite the managed block of .git/info/exclude to list `skill_ids`."""
    path = workspace / EXCLUDE_PATH
    current = path.read_text() if path.is_file() else ""
    if not skill_ids and EXCLUDE_BEGIN not in current:
        return None
    block = "\n".join([EXCLUDE_BEGIN, *(f"/{SKILLS_DIR}/{skill_id}" for skill_id in skill_ids), EXCLUDE_END])
    updated = _replace_block(current, block)
    if updated == current:
        return None
    return Change("write", path, updated, f"rewrite the managed block in {EXCLUDE_PATH}")


def _replace_block(text: str, block: str) -> str:
    """Swap the managed block in `text` for `block`; append one when absent."""
    lines = text.split("\n")
    if EXCLUDE_BEGIN not in lines:
        separator = "" if not text or text.endswith("\n") else "\n"
        return f"{text}{separator}{block}\n"
    start = lines.index(EXCLUDE_BEGIN)
    after = lines[start + 1:]
    if EXCLUDE_END in after:
        rest = lines[after.index(EXCLUDE_END) + start + 2:]
    else:  # an unterminated block runs to the end of the file
        rest = lines[-1:] if lines[-1] == "" else []
    return "\n".join([*lines[:start], *block.split("\n"), *rest])


# ── 2. MCP servers ──────────────────────────────────────────────────


def mcp_change(workspace: Path, manifest: Manifest, servers: dict[str, dict]) -> list[Change]:
    """The OpenCode config edit, when that harness is listed and its block is stale."""
    if "opencode" not in manifest.harnesses:
        return []
    path = workspace / OPENCODE_CONFIG
    if not path.is_file() and not servers:
        return []  # nothing to write; do not create a config just to hold an empty block
    current = path.read_text() if path.is_file() else "{\n}\n"
    updated = splice_mcp_servers(current, servers)
    if updated == current:
        return []
    names = ", ".join(sorted(servers)) or "none"
    return [Change("write", path, updated, f"write mcp.servers in {OPENCODE_CONFIG} ({names})")]


def splice_mcp_servers(raw: str, servers: dict[str, dict]) -> str:
    """`raw` with mcp.servers replaced. Every other byte is kept.

    The block is located textually, so each candidate is parsed and compared
    with the intended configuration before it is trusted.
    """
    try:
        config = json.loads(raw)
    except ValueError as e:
        raise SyncError([f"{OPENCODE_CONFIG}: not valid JSON ({e}); fix it or remove the file"]) from e
    if not isinstance(config, dict) or not isinstance(config.get("mcp", {}), dict):
        raise SyncError([f"{OPENCODE_CONFIG}: the top level and 'mcp' must be objects"])
    config.setdefault("mcp", {})["servers"] = servers
    for candidate in _candidates(raw, servers):
        if json.loads(candidate) == config:
            return candidate
    raise SyncError([f"{OPENCODE_CONFIG}: could not update mcp.servers in place; the file was left untouched"])


SERVERS_KEY = re.compile(r'"servers"\s*:\s*(?=\{)')
MCP_KEY = re.compile(r'"mcp"\s*:\s*(?=\{)')
_DECODER = json.JSONDecoder()


def _candidates(raw: str, servers: dict[str, dict]) -> Iterator[str]:
    """Ways to put `servers` in `raw`: replace, extend, or add the block."""
    unit = _indent_unit(raw)
    for match in SERVERS_KEY.finditer(raw):
        yield _replace_object(raw, match.end(), servers, _key_indent(raw, match.start()), unit)
    for match in MCP_KEY.finditer(raw):
        yield _extend_object(raw, match.end(), "servers", servers, _key_indent(raw, match.start()), unit)
    yield _extend_object(raw, raw.index("{"), "mcp", {"servers": servers}, "", unit)


def _replace_object(raw: str, brace: int, value: object, indent: str, unit: str) -> str:
    """`raw` with the object starting at `brace` swapped for `value`."""
    _, end = _DECODER.raw_decode(raw, brace)
    return raw[:brace] + _render(value, indent, unit) + raw[end:]


def _extend_object(raw: str, brace: int, key: str, value: object, indent: str, unit: str) -> str:
    """`raw` with `key: value` inserted first in the object starting at `brace`."""
    existing, _ = _DECODER.raw_decode(raw, brace)
    if not existing:
        return _replace_object(raw, brace, {key: value}, indent, unit)
    inner = indent + unit
    first = f'\n{inner}"{key}": {_render(value, inner, unit)},'
    return raw[:brace + 1] + first + raw[brace + 1:]


def _render(value: object, indent: str, unit: str) -> str:
    """JSON for `value`, its continuation lines set under a key at `indent`."""
    lines = json.dumps(value, indent=unit).split("\n")
    return lines[0] + "".join(f"\n{indent}{line}" for line in lines[1:])


def _key_indent(raw: str, index: int) -> str:
    return raw[raw.rfind("\n", 0, index) + 1:index]


def _indent_unit(raw: str) -> str:
    """The file's indentation step, read from its first indented line."""
    indented = re.search(r"\n([ \t]+)\S", raw)
    return indented.group(1) if indented else "  "


# ── 3. Jobs ─────────────────────────────────────────────────────────


def job_change(workspace: Path, enabled: dict[str, Pack], cron_state: Path) -> tuple[list[Change], str | None]:
    """enabled.json for the cron runner, and a note when jobs are skipped for lack of one.

    The runner installs job files by filename alone, so two packs shipping
    the same filename is an error, not a silent overwrite.
    """
    jobs = {pack.name: pack.jobs for pack in (local_pack(workspace), *enabled.values()) if pack.jobs}
    path = cron_state / "enabled.json"
    if JOB_RUNNER_PACK not in enabled:
        skipped = [f"packs/{name}/{job}" for name, pack_jobs in jobs.items() for job in pack_jobs]
        note = f"jobs skipped, the '{JOB_RUNNER_PACK}' pack is not enabled: {', '.join(skipped)}" if skipped else None
        stale = [Change("remove", path, detail=f"remove {path} (no job runner enabled)")] if path.exists() else []
        return stale, note
    listed: list[str] = []
    owners: dict[str, str] = {}
    problems: list[str] = []
    for name, pack_jobs in jobs.items():
        for job in pack_jobs:
            listed.append(f"packs/{name}/{job}")
            base = Path(job).name
            if base in owners and owners[base] != name:
                problems.append(
                    f"job file '{base}' ships in both packs/{owners[base]}/ and packs/{name}/; rename one"
                )
            else:
                owners[base] = name
    if problems:
        raise SyncError(problems)
    listed.sort()
    text = json.dumps({"jobs": listed}, indent=2) + "\n"
    if path.is_file() and path.read_text() == text:
        return [], None
    return [Change("write", path, text, f"write {path} ({len(listed)} job(s))")], None


# ── 4. Report ───────────────────────────────────────────────────────


def pack_line(pack: Pack) -> str:
    """One enabled pack as the report prints it."""
    missing = [prereq.cmd for prereq in missing_prereqs(pack)]
    prereqs = f"missing: {', '.join(missing)}" if missing else "ok"
    count = len(pack_skills(pack))
    return f"{pack.name:<12}enabled · {count} skill{'s' if count != 1 else ''} · prereqs {prereqs}"


def prereq_notes(enabled: dict[str, Pack]) -> list[str]:
    notes = []
    for pack in enabled.values():
        for prereq in missing_prereqs(pack):
            hint = install_hint(prereq)
            notes.append(
                f"{pack.name}: '{prereq.cmd}' is missing ({prereq.why}); sync never installs."
                + (f" Install: {hint}" if hint else "")
            )
    return notes


def _shown(workspace: Path, path: Path) -> str:
    return path.relative_to(workspace).as_posix()
