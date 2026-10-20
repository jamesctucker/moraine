#!/usr/bin/env python3
"""Validate work-repos.md registry against the actual work/ directory.

Checks that every repo listed in memory/work-repos.md that is scoped to this
machine exists on disk in work/, and flags repos on disk that aren't in the
registry. Machine scoping comes from frontmatter `machine_scope`; repos with no
scope entry are checked everywhere. The current machine is resolved from the
hostname via MACHINE_ALIASES.

Usage:
    python scripts/workspace/validate-repos.py
    python scripts/workspace/validate-repos.py --fix   # regenerate the registry table
"""

from __future__ import annotations

import argparse
import re
import socket
import sys
from pathlib import Path

from lib import WORKSPACE, parse

WORK_DIR = WORKSPACE / "work"
REPOS_MD = WORKSPACE / "memory" / "work-repos.md"

# Hostname → machine id used in work-repos.md frontmatter `machine_scope`.
# Add your own machines, e.g. {"my-laptop": "laptop", "build-box": "linux"}.
MACHINE_ALIASES: dict[str, str] = {}
# Repos with no machine_scope entry are checked on every machine.
DEFAULT_SCOPE = None

# Parse table rows from work-repos.md main table: | Repo Name | `work/path/` | ... |
# Only matches rows with `work/` in the path column
TABLE_ROW_RE = re.compile(r"^\|\s*\[?([^\]|]+?)\]?(?:\|[^\]]+)?\|\s*`work/([^`]+)`\s*\|")


def current_machine() -> tuple[str, bool]:
    """Resolve this machine's id from the hostname. Returns (id, known)."""
    host = socket.gethostname().strip()
    if host in MACHINE_ALIASES:
        return MACHINE_ALIASES[host], True
    return host, False


def parse_registry(content: str) -> dict[str, str]:
    """Parse work-repos.md main table, return {repo_path: repo_name}.

    Only parses the first table (the "on disk" repos).
    The "Not currently cloned" table is skipped because it uses GitHub URLs.
    """
    repos: dict[str, str] = {}
    in_main_table = False
    seen_header = False

    for line in content.split("\n"):
        stripped = line.strip()

        # Detect table header row
        if stripped.startswith("|") and "Repo" in stripped and "Path" in stripped:
            in_main_table = True
            seen_header = True
            continue

        # Skip separator row
        if in_main_table and stripped.startswith("|") and "---" in stripped:
            continue

        # End of main table
        if in_main_table and (not stripped.startswith("|") or not seen_header):
            if not stripped.startswith("|"):
                in_main_table = False
                seen_header = False
                continue

        if in_main_table and stripped.startswith("|"):
            m = TABLE_ROW_RE.search(stripped)
            if m:
                name = m.group(1).strip()
                path = m.group(2).strip()
                repos[path] = name

    return repos


def find_disk_repos() -> dict[str, Path]:
    """Find all directories in work/ that look like git repos."""
    repos: dict[str, Path] = {}
    if not WORK_DIR.is_dir():
        return repos
    for child in sorted(WORK_DIR.iterdir()):
        if child.is_dir() and not child.name.startswith(".") and child.name != "__pycache__":
            repos[child.name] = child
    return repos


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate work-repos.md registry against actual work/ directory"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Print a regenerated registry table (does not write)",
    )
    args = parser.parse_args()

    if not REPOS_MD.exists():
        print(f"error: {REPOS_MD} not found", file=sys.stderr)
        sys.exit(1)

    content = REPOS_MD.read_text()
    fm, _body = parse(content)
    machine_scope_raw = (fm or {}).get("machine_scope") or {}
    machine, machine_known = current_machine()
    registry = parse_registry(content)
    disk_repos = find_disk_repos()

    machine_scope: dict[str, list[str]] = {}
    for key, val in machine_scope_raw.items():
        machine_scope[key] = [str(val)] if isinstance(val, str) else [str(m) for m in val]

    # Normalize registry paths: they look like work/my-app/
    registry_dirs = {}
    for path_str, name in registry.items():
        # Strip work/ prefix if present
        dir_name = path_str.replace("work/", "").strip("/")
        registry_dirs[dir_name] = name

    errors: list[str] = []
    warnings: list[str] = []

    # Only warn about an unmapped hostname when the registry actually uses scoping.
    if not machine_known and machine_scope:
        warnings.append(
            f"Unknown machine '{machine}' — not in validate-repos.py MACHINE_ALIASES; "
            "add it there and to machine_scope entries"
        )

    # Scope keys that don't match a registry row (typo guard)
    for key in sorted(machine_scope):
        if key not in registry_dirs:
            warnings.append(
                f"machine_scope key '{key}' matches no registry row (typo?)"
            )

    # Check registry repos expected on THIS machine exist on disk
    for dir_name, repo_name in sorted(registry_dirs.items()):
        machines = machine_scope.get(dir_name, DEFAULT_SCOPE)
        if machines is not None and machine not in machines:
            continue
        if dir_name not in disk_repos:
            errors.append(
                f"MISSING: '{repo_name}' (work/{dir_name}/) is in registry but not on disk"
            )

    # Check disk repos are in registry
    for dir_name in sorted(disk_repos):
        if dir_name not in registry_dirs:
            # Skip non-repo directories
            child = disk_repos[dir_name]
            if not (child / ".git").exists():
                continue
            warnings.append(
                f"UNREGISTERED: work/{dir_name}/ exists on disk but is not in work-repos.md"
            )

    # Print results
    print(f"Machine: {machine}" + ("" if machine_known else " (unknown)"))
    print(f"Registry: {len(registry_dirs)} repos")
    print(f"Disk: {len([d for d in disk_repos.values() if (d / '.git').exists()])} git repos")
    print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
        print()

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠ {w}")
        print()

    if not errors and not warnings:
        print("✓ Registry matches disk — all repos accounted for.")
    elif not errors:
        print("✓ All registered repos exist on disk (some unregistered dirs on disk).")

    if args.fix:
        print("\n--- Regenerated registry table (review and paste into work-repos.md) ---\n")
        print("| Repo | Path | Stack | Issue Tracker | AGENTS.md |")
        print("|------|------|-------|---------------|-----------|")
        for dir_name in sorted(set(list(registry_dirs.keys()) + list(disk_repos.keys()))):
            child = disk_repos.get(dir_name)
            if child and (child / ".git").exists():
                name = registry_dirs.get(dir_name, dir_name)
                print(f"| {name} | `work/{dir_name}/` | — | — | — |")
            elif dir_name in registry_dirs:
                name = registry_dirs[dir_name]
                print(f"| {name} | `work/{dir_name}/` | — | — | — | (MISSING on disk) |")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
