"""The repos/ registry: pointer files for the repos this workspace works on.

`repos/README.md` holds a Repos table (and past about 20 repos, an Areas
table whose rows point at area files that each hold their own Repos table):

    ## Repos

    | Repo | What it is | Path | Remote | Hint |
    |------|------------|------|--------|------|
    | storefront | Next.js app | repos/storefront | git@github.com:acme/storefront.git | Read its AGENTS.md first |

Rules, enforced by `load_registry`:

- `Path` is relative to the workspace root, or starts with `~/`.
- `Remote` is required — it is what makes `restore` possible.
- The optional `Machines` column is comma-separated hostnames; empty means
  every machine.
- A file has either a Repos table or an Areas table, not both, and each repo
  is listed once across all files.

`check` is flag-only: it never clones, moves, or writes anything. `restore`
clones, showing the exact command and asking first.
"""

from __future__ import annotations

import re
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from lib import WORKSPACE

REPOS_DIR = "repos"
README = "repos/README.md"
REPO_COLUMNS = {"Repo", "What it is", "Path", "Remote"}
AREA_COLUMNS = {"Area", "Covers", "File"}
# Hint and Machines are optional; anything else is a typo worth naming.
KNOWN_COLUMNS = REPO_COLUMNS | AREA_COLUMNS | {"Hint", "Machines"}

_SEPARATOR = re.compile(r"^:?-+:?$")


@dataclass(frozen=True)
class Repo:
    name: str
    what: str
    path: str  # as written: "repos/<name>" or "~/code/<name>"
    remote: str
    hint: str = ""
    machines: tuple[str, ...] = ()
    where: str = README  # the file the row was read from


# ── Parsing ─────────────────────────────────────────────────────────


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Every markdown table in `text`: (header cells, data rows)."""
    lines = text.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.startswith("|") or index + 1 >= len(lines):
            index += 1
            continue
        separator = _cells(lines[index + 1])
        if not all(_SEPARATOR.match(cell) for cell in separator if cell):
            index += 1
            continue
        rows: list[list[str]] = []
        after = index + 2
        while after < len(lines) and lines[after].startswith("|"):
            rows.append(_cells(lines[after]))
            after += 1
        tables.append((_cells(line), rows))
        index = after
    return tables


def load_registry(workspace: Path = WORKSPACE) -> tuple[list[Repo], list[str]]:
    """Every registered repo, and every problem found while reading them."""
    readme = workspace / README
    if not readme.is_file():
        return [], [f"{README}: not found — the registry lives there"]
    text = readme.read_text()
    repos, problems = _repos_table(readme, text)
    areas = [
        row[2]
        for header, rows in _tables(text)
        if set(header) & AREA_COLUMNS == AREA_COLUMNS
        for row in rows
        if len(row) > 2 and row[2]
    ]
    for area in areas:
        # The File column holds a workspace-relative path ("repos/billing.md");
        # a bare name means the same file.
        path = workspace / area if area.endswith(".md") else workspace / REPOS_DIR / f"{area}.md"
        if not path.is_file():
            problems.append(f"{README}: area file {area} does not exist")
            continue
        found, area_problems = _repos_table(path, path.read_text())
        repos += found
        problems += area_problems
    return repos, problems


def _repos_table(path: Path, text: str) -> tuple[list[Repo], list[str]]:
    """The Repos rows in one file, with per-file problems."""
    repos: list[Repo] = []
    problems: list[str] = []
    saw_areas = False
    for header, rows in _tables(text):
        columns = set(header)
        if not columns & (REPO_COLUMNS | AREA_COLUMNS):
            continue  # an unrelated table (hint lists, examples) is not ours
        unknown = sorted(columns - KNOWN_COLUMNS)
        if unknown:
            problems.append(f"{path.name}: unknown column(s) {', '.join(unknown)}")
        if REPO_COLUMNS <= columns:
            repos += [_repo(path, header, row) for row in rows if _filled(row)]
        elif AREA_COLUMNS <= columns:
            saw_areas = True
        else:
            wanted = REPO_COLUMNS if columns & REPO_COLUMNS else AREA_COLUMNS
            missing = sorted(wanted - columns)
            problems.append(f"{path.name}: a table is missing column(s) {', '.join(missing)}")
    if saw_areas and repos:
        problems.append(f"{path.name}: has both a Repos table and an Areas table")
    return repos, problems


def _filled(row: list[str]) -> bool:
    return any(cell for cell in row)


def _repo(path: Path, header: list[str], row: list[str]) -> Repo:
    values = dict(zip(header, row))
    return Repo(
        name=values.get("Repo", ""),
        what=values.get("What it is", ""),
        path=values.get("Path", "").rstrip("/"),
        remote=values.get("Remote", ""),
        hint=values.get("Hint", ""),
        machines=tuple(m.strip() for m in values.get("Machines", "").split(",") if m.strip()),
        where=str(path.relative_to(path.parents[1])) if len(path.parents) > 1 else path.name,
    )


def registry_problems(repos: list[Repo]) -> list[str]:
    """The rules a loaded registry can still break: names, remotes, paths."""
    problems: list[str] = []
    seen: dict[str, str] = {}
    for repo in repos:
        if not repo.name:
            problems.append(f"{repo.where}: a row with no Repo name")
        elif repo.name in seen:
            problems.append(f"'{repo.name}' is listed in both {seen[repo.name]} and {repo.where}")
        else:
            seen[repo.name] = repo.where
        if not repo.remote:
            problems.append(f"{repo.where}: '{repo.name}' has no Remote — restore needs one")
        if not repo.path:
            problems.append(f"{repo.where}: '{repo.name}' has no Path")
        elif repo.path.startswith("/") or ".." in Path(repo.path).parts:
            problems.append(f"{repo.where}: '{repo.name}' path {repo.path!r} must be relative or start with ~/")
    return problems


# ── Where a repo lives ───────────────────────────────────────────────


def hostname() -> str:
    # macOS Computer Names can carry trailing whitespace — trim so the
    # Machines column can be written cleanly.
    return socket.gethostname().split(".")[0].strip()


def on_this_machine(repo: Repo, host: str | None = None) -> bool:
    if not repo.machines:
        return True
    host = host or hostname()
    return any(machine == host for machine in repo.machines)


def resolve(workspace: Path, path: str) -> Path:
    if path.startswith("~/"):
        return Path(path).expanduser()
    return (workspace / path).resolve()


# ── check ───────────────────────────────────────────────────────────


def origin(path: Path) -> str | None:
    """The path's origin URL, or None when it has none (or isn't a repo)."""
    result = subprocess.run(
        ["git", "-C", str(path), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def check(workspace: Path = WORKSPACE, host: str | None = None) -> list[str]:
    """Flag-only findings: missing repos, unregistered clones, remote drift."""
    repos, problems = load_registry(workspace)
    findings = problems + registry_problems(repos)
    for repo in repos:
        if not on_this_machine(repo, host):
            continue
        path = resolve(workspace, repo.path)
        if not path.is_dir():
            findings.append(f"missing: '{repo.name}' ({repo.path}) — clone it with: moraine repos restore")
            continue
        if not (path / ".git").exists():
            findings.append(f"not a git repo: '{repo.name}' at {repo.path}")
            continue
        url = origin(path)
        if url is None:
            findings.append(f"no origin: '{repo.name}' has no origin remote (registry says {repo.remote})")
        elif url != repo.remote:
            findings.append(f"remote drift: '{repo.name}' origin is {url}, registry says {repo.remote}")
    registered = {repo.path for repo in repos}
    clones = workspace / REPOS_DIR
    if clones.is_dir():
        for entry in sorted(clones.iterdir()):
            if not (entry / ".git").exists():
                continue  # only clones; the registry files themselves are not repos
            if f"{REPOS_DIR}/{entry.name}" not in registered:
                findings.append(f"unregistered clone: {REPOS_DIR}/{entry.name} is not in the registry")
    return findings


# ── restore ──────────────────────────────────────────────────────────


def missing_repos(workspace: Path = WORKSPACE, host: str | None = None) -> list[Repo]:
    """Registered repos this machine should have but doesn't.

    Rows without a Remote are left out: the registry problem already names
    them, and there is nothing to clone from.
    """
    repos, _ = load_registry(workspace)
    return [
        repo
        for repo in repos
        if repo.remote and on_this_machine(repo, host) and not resolve(workspace, repo.path).is_dir()
    ]


def clone_command(workspace: Path, repo: Repo) -> list[str]:
    return ["git", "clone", repo.remote, str(resolve(workspace, repo.path))]


def restore(workspace: Path = WORKSPACE, assume_yes: bool = False, host: str | None = None) -> int:
    """Clone each missing repo for this machine, asking before every clone."""
    missing = missing_repos(workspace, host)
    if not missing:
        print("No missing repos for this machine.")
        return 0
    failed = 0
    for repo in missing:
        command = clone_command(workspace, repo)
        shown = " ".join(command)
        print(f"\n  {repo.name} → {repo.path}")
        print(f"  {shown}")
        if not assume_yes:
            print("  clone it? [Y/n] ", end="", flush=True)
            answer = sys.stdin.readline().strip().lower()
            if answer and answer not in ("y", "yes"):
                print("  skipped")
                continue
        target = resolve(workspace, repo.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if shutil.which("git") is None:
            print("  error: git not on PATH", file=sys.stderr)
            failed += 1
            continue
        if subprocess.run(command).returncode != 0:
            failed += 1
    print(f"\n{len(missing) - failed} cloned, {failed} failed.")
    return 1 if failed else 0


# ── CLI entry ───────────────────────────────────────────────────────


def main(argv: list[str], workspace: Path = WORKSPACE) -> int:
    """`moraine repos check|restore` — thin dispatch, real logic above."""
    if argv[:1] == ["check"]:
        findings = check(workspace)
        for finding in findings:
            print(f"  {finding}")
        print("repos check: clean" if not findings else f"repos check: {len(findings)} finding(s)")
        return 0
    if argv[:1] == ["restore"]:
        return restore(workspace, assume_yes="--yes" in argv or "-y" in argv[1:])
    print("usage: moraine repos <check|restore> [--yes]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
