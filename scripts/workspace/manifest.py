"""Pack and workspace manifests: moraine.yaml and packs/<name>/pack.yaml.

Both are checked against one strict schema here, so `moraine sync`,
`moraine packs`, `validate.py`, and `health-check.py` agree on what is valid.
Unknown keys are rejected so a typo cannot be silently ignored.

moraine.yaml
    version: 1
    harnesses: [opencode]        # any of HARNESSES
    packs: [engineering]         # shipped pack names; `local` is never listed
    mcp: {name: server}          # the user's servers

packs/<name>/pack.yaml
    name, description
    requires: [pack]             # enabled together with this pack
    harnesses: [any | opencode | claude | codex]
    prereqs: [{cmd, why, install}]      # install: one command, or {macos, linux} commands
    mcp: {name: server}
    jobs: [jobs/<name>.yaml]     # relative to the pack folder

A server is `{type: local, command: [...]}` or `{type: remote, url}`. Any other
key on a server is passed through to the harness untouched.
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from lib import WORKSPACE, skill_dirs

PACKS_DIR = "packs"
# The user's own pack has no pack.yaml: it is always on and never listed.
LOCAL_PACK = "local"
HARNESSES = ("opencode", "claude", "codex")
ANY_HARNESS = "any"

MANIFEST_NAME = "moraine.yaml"
MANIFEST_KEYS = {"version", "harnesses", "packs", "mcp"}
PACK_KEYS = {"name", "description", "requires", "harnesses", "prereqs", "mcp", "jobs"}
PREREQ_KEYS = {"cmd", "why", "install"}
INSTALL_PLATFORMS = {"macos", "linux", "windows"}

PACK_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ManifestError(Exception):
    """The manifests are not valid. `problems` lists every issue found."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Prereq:
    cmd: str
    why: str
    install: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Pack:
    name: str
    path: Path
    description: str
    requires: tuple[str, ...] = ()
    harnesses: tuple[str, ...] = (ANY_HARNESS,)
    prereqs: tuple[Prereq, ...] = ()
    mcp: dict[str, dict] = field(default_factory=dict)
    jobs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Manifest:
    harnesses: tuple[str, ...]
    packs: tuple[str, ...]
    mcp: dict[str, dict] = field(default_factory=dict)


# ── Loading ─────────────────────────────────────────────────────────


def load_manifests(workspace: Path = WORKSPACE) -> tuple[Manifest, dict[str, Pack]]:
    """Load and check moraine.yaml and every shipped pack.

    Raises ManifestError with every problem found, so one run reports them all.
    """
    manifest, problems = _load_manifest_file(workspace)
    packs, pack_problems = _load_packs(workspace)
    problems += pack_problems
    if not problems:
        problems = _cross_check(manifest, packs)
    if problems:
        raise ManifestError(problems)
    return manifest, packs


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        mark = e.problem_mark
        where = f"{path.name}:{mark.line + 1}" if mark else path.name
        raise ManifestError([f"{where}: {e.problem}"]) from e


def _load_manifest_file(workspace: Path) -> tuple[Manifest, list[str]]:
    path = workspace / MANIFEST_NAME
    if not path.is_file():
        return Manifest((), ()), [f"{MANIFEST_NAME}: not found (bash scripts/setup creates it)"]
    data = _read_yaml(path)
    problems = _check_keys(MANIFEST_NAME, data, MANIFEST_KEYS, required={"version"})
    if not isinstance(data, dict):
        return Manifest((), ()), problems
    problems += _check_manifest_fields(data)
    if problems:
        return Manifest((), ()), problems
    return Manifest(tuple(data.get("harnesses", [])), tuple(data.get("packs", [])), dict(data.get("mcp", {}))), []


def _check_manifest_fields(data: dict[str, Any]) -> list[str]:
    where = MANIFEST_NAME
    if data.get("version") != 1:
        problems = [f"{where}: version {data.get('version')!r} is not supported; this Moraine reads version 1"]
    else:
        problems = []
    harnesses = data.get("harnesses", [])
    problems += _check_names(f"{where}: harnesses", harnesses, set(HARNESSES))
    listed = data.get("packs", [])
    problems += _check_names(f"{where}: packs", listed, None)
    if isinstance(listed, list) and LOCAL_PACK in listed:
        problems.append(f"{where}: '{LOCAL_PACK}' is always enabled; do not list it")
    problems += _check_servers(f"{where}: mcp", data.get("mcp", {}))
    return problems


def _load_packs(workspace: Path) -> tuple[dict[str, Pack], list[str]]:
    """Every packs/<name>/pack.yaml. A pack with problems is left out."""
    packs: dict[str, Pack] = {}
    problems: list[str] = []
    for path in sorted((workspace / PACKS_DIR).glob("*/pack.yaml")):
        name = path.parent.name
        where = f"{PACKS_DIR}/{name}/pack.yaml"
        data = _read_yaml(path)
        found = _check_keys(where, data, PACK_KEYS, required={"name", "description"})
        if not found:
            found = _check_pack(where, name, path.parent, data)
        problems += found
        if not found:
            packs[name] = _pack(name, path.parent, data)
    return packs, problems


def _check_pack(where: str, name: str, folder: Path, data: dict[str, Any]) -> list[str]:
    if data["name"] != name:
        found = [f"{where}: name {data['name']!r} does not match the folder '{name}'"]
    elif not PACK_NAME_RE.match(name):
        found = [f"{where}: pack name '{name}' is not kebab-case"]
    else:
        found = []
    if not isinstance(data["description"], str) or not data["description"].strip():
        found.append(f"{where}: description must be a non-empty string")
    found += _check_names(f"{where}: requires", data.get("requires", []), None)
    found += _check_pack_harnesses(f"{where}: harnesses", data.get("harnesses", [ANY_HARNESS]))
    found += _check_prereqs(f"{where}: prereqs", data.get("prereqs", []))
    found += _check_servers(f"{where}: mcp", data.get("mcp", {}))
    found += _check_jobs(where, folder, data.get("jobs", []))
    return found


def _pack(name: str, folder: Path, data: dict[str, Any]) -> Pack:
    """Build a pack from data that passed _check_pack."""
    prereqs = tuple(
        Prereq(entry["cmd"], entry["why"], _install_commands(entry.get("install")))
        for entry in data.get("prereqs", [])
    )
    return Pack(
        name=name,
        path=folder,
        description=data["description"],
        requires=tuple(data.get("requires", ())),
        harnesses=tuple(data.get("harnesses", (ANY_HARNESS,))),
        prereqs=prereqs,
        mcp=dict(data.get("mcp", {})),
        jobs=tuple(data.get("jobs", ())),
    )


# ── Shape checks. Each returns the problems it found, in full. ───────


def _check_keys(where: str, data: object, allowed: set[str], required: set[str]) -> list[str]:
    if not isinstance(data, dict):
        return [f"{where}: must be a mapping"]
    problems = [f"{where}: unknown key '{key}'" for key in sorted(set(data) - allowed)]
    problems += [f"{where}: missing required key '{key}'" for key in sorted(required - set(data))]
    return problems


def _check_names(where: str, value: object, known: set[str] | None) -> list[str]:
    """A list of unique strings; when `known` is given, every name is in it."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return [f"{where}: must be a list of names"]
    if len(set(value)) != len(value):
        return [f"{where}: names must be unique"]
    if known is not None and (unknown := sorted(set(value) - known)):
        return [f"{where}: unknown name {', '.join(map(repr, unknown))}; allowed: {', '.join(sorted(known))}"]
    return []


def _check_pack_harnesses(where: str, value: object) -> list[str]:
    allowed = {ANY_HARNESS, *HARNESSES}
    if value == []:
        return [f"{where}: cannot be empty; use [{ANY_HARNESS}]"]
    problems = _check_names(where, value, allowed)
    if not problems and ANY_HARNESS in value and len(value) > 1:
        problems = [f"{where}: '{ANY_HARNESS}' cannot be combined with other harnesses"]
    return problems


def _install_commands(install: object) -> dict[str, str]:
    """Per-platform install commands; one string applies everywhere."""
    if isinstance(install, str):
        return dict.fromkeys(INSTALL_PLATFORMS, install)
    return dict(install or {})


def _check_prereqs(where: str, value: object) -> list[str]:
    if not isinstance(value, list):
        return [f"{where}: must be a list"]
    problems: list[str] = []
    for index, entry in enumerate(value):
        at = f"{where}[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{at}: must be a mapping")
            continue
        problems += _check_keys(at, entry, PREREQ_KEYS, required={"cmd", "why"})
        if not isinstance(entry.get("cmd"), str) or not isinstance(entry.get("why"), str):
            problems.append(f"{at}: cmd and why must be strings")
        problems += _check_install(f"{at}.install", entry.get("install"))
    return problems


def _check_install(where: str, install: object) -> list[str]:
    """`install` is one command string, or a platform -> command mapping."""
    if install is None or isinstance(install, str):
        return []
    if not isinstance(install, dict) or not all(isinstance(command, str) for command in install.values()):
        return [f"{where}: must be a command, or map a platform to a command"]
    return [f"{where}: unknown platform '{platform}'" for platform in sorted(set(install) - INSTALL_PLATFORMS)]


def _check_jobs(where: str, folder: Path, value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(job, str) for job in value):
        return [f"{where}: jobs must be a list of paths relative to the pack folder"]
    return [f"{where}: job '{job}' is not a file in the pack" for job in value if not _inside(folder, folder / job)]


def _inside(folder: Path, path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        path.resolve().relative_to(folder.resolve())
    except ValueError:
        return False
    return True


def _check_servers(where: str, value: object) -> list[str]:
    if not isinstance(value, dict):
        return [f"{where}: must be a mapping of server name to config"]
    problems = []
    for name, server in value.items():
        at = f"{where}.{name}"
        if not isinstance(server, dict) or server.get("type") not in ("local", "remote"):
            problems.append(f"{at}: type must be 'local' or 'remote'")
        elif server["type"] == "local":
            command = server.get("command")
            if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
                problems.append(f"{at}: a local server needs a non-empty 'command' list of strings")
        elif not isinstance(server.get("url"), str) or not server["url"].strip():
            problems.append(f"{at}: a remote server needs a 'url'")
    return problems


# ── Cross-checks: problems that only show once both manifests are read ──


def _cross_check(manifest: Manifest, packs: dict[str, Pack]) -> list[str]:
    unknown = [f"{MANIFEST_NAME}: unknown pack '{name}'" for name in manifest.packs if name not in packs]
    for pack in packs.values():
        unknown += [
            f"{PACKS_DIR}/{pack.name}/pack.yaml: requires unknown pack '{dep}'"
            for dep in pack.requires
            if dep not in packs or dep == pack.name
        ]
    cycles = [f"requires cycle: {cycle}" for cycle in _require_cycles(packs)]
    if unknown:
        # Harnesses and servers are resolved through pack names, so they
        # can only be checked once every name resolves.
        return unknown + cycles
    enabled = enabled_packs(manifest.packs, packs)
    _, collisions = merged_mcp(manifest, enabled)
    return cycles + _unfitted_harnesses(manifest, enabled) + collisions


def _require_cycles(packs: dict[str, Pack]) -> list[str]:
    """Every cycle in `requires`, each reported once as a -> b -> a."""
    cycles: list[str] = []
    reported: set[frozenset[str]] = set()

    def walk(name: str, chain: list[str]) -> None:
        for dep in packs[name].requires:
            if dep not in packs:
                continue
            if dep in chain:
                cycle = chain[chain.index(dep):] + [dep]
                if frozenset(cycle) not in reported:
                    reported.add(frozenset(cycle))
                    cycles.append(" -> ".join(cycle))
            else:
                walk(dep, chain + [dep])

    for name in sorted(packs):
        walk(name, [name])
    return cycles


def _unfitted_harnesses(manifest: Manifest, enabled: dict[str, Pack]) -> list[str]:
    """Enabled packs that need a harness moraine.yaml does not list."""
    return [
        f"{PACKS_DIR}/{pack.name}/pack.yaml: needs the {', '.join(pack.harnesses)} harness, "
        f"but {MANIFEST_NAME} lists {', '.join(manifest.harnesses) or 'none'}"
        for pack in enabled.values()
        if not harness_fits(pack, manifest.harnesses)
    ]


# ── Queries ─────────────────────────────────────────────────────────


def enabled_packs(listed: tuple[str, ...], packs: dict[str, Pack]) -> dict[str, Pack]:
    """The listed packs plus everything they require, transitively, by name."""
    enabled: dict[str, Pack] = {}
    pending = list(listed)
    while pending:
        name = pending.pop()
        if name not in enabled:
            enabled[name] = packs[name]
            pending.extend(enabled[name].requires)
    return dict(sorted(enabled.items()))


def local_pack(workspace: Path = WORKSPACE) -> Pack:
    """The user's own pack. It has no manifest, so its jobs are read from jobs/."""
    path = workspace / PACKS_DIR / LOCAL_PACK
    jobs = tuple(sorted(f"jobs/{job.name}" for job in (path / "jobs").glob("*.yaml")))
    return Pack(name=LOCAL_PACK, path=path, description="Your own skills, conventions, docs, and jobs.", jobs=jobs)


def harness_fits(pack: Pack, harnesses: tuple[str, ...]) -> bool:
    return ANY_HARNESS in pack.harnesses or bool(set(pack.harnesses) & set(harnesses))


def pack_skills(pack: Pack) -> list[Path]:
    return skill_dirs(pack.path / "skills")


def merged_mcp(manifest: Manifest, enabled: dict[str, Pack]) -> tuple[dict[str, dict], list[str]]:
    """The enabled packs' servers plus the user's, and every name defined twice."""
    servers: dict[str, dict] = {}
    defined_in: dict[str, str] = {}
    problems: list[str] = []
    sources = [(f"packs/{pack.name}/pack.yaml", pack.mcp) for pack in enabled.values()]
    sources.append((MANIFEST_NAME, manifest.mcp))
    for source, entries in sources:
        for name, server in entries.items():
            if name in defined_in:
                problems.append(f"MCP server '{name}' is defined in both {defined_in[name]} and {source}; rename one")
            defined_in[name] = source
            servers[name] = server
    return servers, problems


def prereq_met(cmd: str) -> bool:
    """A command on PATH, or a desktop app of that name in an Applications folder."""
    if shutil.which(cmd):
        return True
    app = f"{cmd.capitalize()}.app"
    return any((folder / app).is_dir() for folder in (Path("/Applications"), Path.home() / "Applications"))


def missing_prereqs(pack: Pack) -> list[Prereq]:
    return [prereq for prereq in pack.prereqs if not prereq_met(prereq.cmd)]


def install_hint(prereq: Prereq) -> str | None:
    """The install command for this platform, when the pack gives one."""
    platform = {"darwin": "macos", "linux": "linux"}.get(sys.platform, "")
    return prereq.install.get(platform)


def write_manifest(path: Path, harnesses: list[str] | None = None, packs: list[str] | None = None) -> None:
    """Set `harnesses` and/or `packs` in moraine.yaml, keeping every other byte.

    The value's span comes from the YAML node tree, so comments, key order,
    and formatting elsewhere survive. The edit is re-parsed and compared with
    the intended result before anything is written.
    """
    raw = path.read_text()
    expected = dict(yaml.safe_load(raw))
    candidate = raw
    if harnesses is not None:
        expected["harnesses"] = harnesses
        candidate = _replace_value(candidate, "harnesses", "[" + ", ".join(harnesses) + "]")
    if packs is not None:
        expected["packs"] = packs
        candidate = _replace_value(candidate, "packs", "[" + ", ".join(packs) + "]")
    if yaml.safe_load(candidate) != expected:
        raise ManifestError([f"{MANIFEST_NAME}: could not edit the manifest; edit it by hand"])
    path.write_text(candidate)


def _replace_value(raw: str, key: str, rendered: str) -> str:
    """`raw` with top-level `key`'s value replaced; the key is appended when absent."""
    try:
        root = yaml.compose(raw)
    except yaml.YAMLError as e:
        raise ManifestError([f"{MANIFEST_NAME}: {e.problem}"]) from e
    if isinstance(root, yaml.MappingNode):
        for key_node, value_node in root.value:
            if key_node.value == key:
                start, end = value_node.start_mark.index, value_node.end_mark.index
                while end > start and raw[end - 1] in "\r\n":  # a block list's span ends after its newline
                    end -= 1
                return raw[:start] + rendered + raw[end:]
    separator = "" if not raw or raw.endswith("\n") else "\n"
    return f"{raw}{separator}{key}: {rendered}\n"
