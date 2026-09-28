#!/usr/bin/env python3
"""Verify deployment environment variables across config files.

Detects config drift: env vars referenced in deploy configs, .env files,
Kamal secrets, and application.yml that don't match each other. Catches
stale var names, missing definitions, and vars declared in one place but
not another.

Usage:
    python scripts/workspace/verify-deploy-vars.py                      # scan all work/ repos
    python scripts/workspace/verify-deploy-vars.py --repo my-app        # scan one repo
    python scripts/workspace/verify-deploy-vars.py --repo api-server    # scan a different repo
    python scripts/workspace/verify-deploy-vars.py --strict              # exit 1 on warnings
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from lib import WORKSPACE

WORK_DIR = WORKSPACE / "work"

# Patterns that capture env var references in different file types:

# Rails application.yml: KEY: value
RAILS_YAML_KEY_RE = re.compile(r"^(\w+):\s*", re.MULTILINE)

# .env files: export KEY=value  or  KEY=value
ENV_KEY_RE = re.compile(r"^(?:export\s+)?([A-Z][A-Z0-9_]*)=", re.MULTILINE)

# Kamal secrets files: KEY (one per line, no =)
KAMAL_SECRET_RE = re.compile(r"^([A-Z][A-Z0-9_]*)\s*$", re.MULTILINE)

# ERB env refs in Ruby: ENV["KEY"] or ENV.fetch("KEY", ...)
ERB_ENV_RE = re.compile(r'ENV(?:\[|\.fetch\()\s*["\']([A-Z][A-Z0-9_]*)["\']')

# Shell scripts: $KEY or ${KEY}
SHELL_VAR_RE = re.compile(r"\$\{?([A-Z][A-Z0-9_]*)\}?")

# Glob patterns for each config file category
CONFIG_GLOBS = {
    "application.yml": ["**/config/application.yml", "**/config/application*.yml"],
    "env": ["**/.env*", "**/.envrc"],
    "kamal_secrets": ["**/.kamal/secrets*", "**/config/secrets*.yml"],
    "deploy": ["**/config/deploy*.yml", "**/deploy*.yml"],
    "shell_scripts": ["**/bin/deploy*", "**/bin/*deploy*", "**/deploy.sh", "**/scripts/deploy*.sh"],
}


@dataclass
class VarSource:
    """Where an env var was found."""
    file: Path
    context: str  # which config category


@dataclass
class RepoReport:
    """Deploy var analysis for one repo."""
    repo_name: str
    repo_path: Path
    # var_name -> list of sources
    vars: dict[str, list[VarSource]] = field(default_factory=lambda: defaultdict(list))
    files_scanned: list[Path] = field(default_factory=list)


def find_repos() -> list[Path]:
    """Find all subdirectories in work/ that look like git repos."""
    repos = []
    if not WORK_DIR.is_dir():
        return repos
    for child in sorted(WORK_DIR.iterdir()):
        if child.is_dir() and (child / ".git").exists():
            repos.append(child)
    return repos


def scan_repo(repo_path: Path) -> RepoReport:
    """Scan a single repo for env var references across all config file types."""
    report = RepoReport(
        repo_name=repo_path.name,
        repo_path=repo_path,
    )

    for context, globs in CONFIG_GLOBS.items():
        for pattern in globs:
            for filepath in repo_path.glob(pattern):
                if filepath.is_file():
                    report.files_scanned.append(filepath)
                    _extract_vars(filepath, context, report)

    return report


def _extract_vars(filepath: Path, context: str, report: RepoReport) -> None:
    """Extract env var names from a file based on its category."""
    try:
        content = filepath.read_text(errors="ignore")
    except Exception:
        return

    patterns: list[re.Pattern] = []
    fname = filepath.name

    if fname.startswith(".env") or fname == ".envrc":
        patterns = [ENV_KEY_RE]
    elif "secrets" in fname.lower():
        # Kamal secrets: KEY per line
        if filepath.suffix in ("", ".yml", ".yaml"):
            patterns = [KAMAL_SECRET_RE, ENV_KEY_RE]
    elif "deploy" in fname.lower() or filepath.suffix in (".sh",):
        patterns = [ERB_ENV_RE, SHELL_VAR_RE, ENV_KEY_RE]
    elif fname.endswith(".yml") or fname.endswith(".yaml"):
        patterns = [RAILS_YAML_KEY_RE, ERB_ENV_RE]
    else:
        patterns = [ERB_ENV_RE, ENV_KEY_RE]

    for pat in patterns:
        for m in pat.finditer(content):
            var_name = m.group(1)
            # Filter out common false positives
            if var_name in ("PATH", "HOME", "USER", "SHELL", "LANG", "LC_ALL", "PWD"):
                continue
            if len(var_name) < 3:
                continue
            source = VarSource(file=filepath.relative_to(report.repo_path), context=context)
            if source not in report.vars[var_name]:
                report.vars[var_name].append(source)


def analyze_drift(reports: list[RepoReport]) -> list[str]:
    """Find vars that appear in some configs but not others within a repo."""
    warnings: list[str] = []

    for report in reports:
        if not report.vars:
            continue

        # Group vars by which config categories they appear in
        var_categories: dict[str, set[str]] = {}
        for var_name, sources in report.vars.items():
            cats = {s.context for s in sources}
            var_categories[var_name] = cats

        # Check for vars in .env but not in application.yml (or vice versa)
        env_vars = {v for v, cats in var_categories.items() if "env" in cats}
        yml_vars = {v for v, cats in var_categories.items() if "application.yml" in cats}

        if env_vars and yml_vars:
            only_env = env_vars - yml_vars
            only_yml = yml_vars - env_vars

            for v in sorted(only_env):
                warnings.append(
                    f"[{report.repo_name}] '{v}' in .env but not in application.yml — possible stale var"
                )
            for v in sorted(only_yml):
                warnings.append(
                    f"[{report.repo_name}] '{v}' in application.yml but not in .env — may need .env entry"
                )

        # Check for vars in deploy scripts that aren't in .env or application.yml
        deploy_vars = {v for v, cats in var_categories.items() if "deploy" in cats or "shell_scripts" in cats}
        defined_vars = env_vars | yml_vars
        if deploy_vars and defined_vars:
            undocumented = deploy_vars - defined_vars
            for v in sorted(undocumented):
                # Filter shell builtins and common vars
                if v not in ("BASH", "BIN", "DIR", "APP", "SERVER", "PORT"):
                    warnings.append(
                        f"[{report.repo_name}] '{v}' referenced in deploy script but not in .env or application.yml"
                    )

    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify deployment env vars across config files"
    )
    parser.add_argument(
        "--repo",
        type=str,
        metavar="NAME",
        help="Scan a single repo in work/ by name",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any warnings are found",
    )
    args = parser.parse_args()

    if args.repo:
        repo_path = WORK_DIR / args.repo
        if not repo_path.is_dir():
            print(f"error: work/{args.repo} not found", file=sys.stderr)
            sys.exit(1)
        repos = [repo_path]
    else:
        repos = find_repos()

    if not repos:
        print("No repos found in work/")
        sys.exit(0)

    print(f"Scanning {len(repos)} repo(s) for deploy var drift...\n")

    reports: list[RepoReport] = []
    for repo in repos:
        report = scan_repo(repo)
        reports.append(report)

    # Print per-repo summary
    for report in reports:
        if not report.files_scanned:
            continue
        print(f"── {report.repo_name} ──────────────────────────────────────")
        print(f"  Files scanned: {len(report.files_scanned)}")
        for f in sorted(report.files_scanned):
            print(f"    {f}")
        print(f"  Unique env vars found: {len(report.vars)}")
        if report.vars:
            # Group by context
            by_context: dict[str, list[str]] = defaultdict(list)
            for var, sources in sorted(report.vars.items()):
                for s in sources:
                    by_context[s.context].append(var)
            for ctx, vars_list in sorted(by_context.items()):
                print(f"    {ctx}: {', '.join(sorted(set(vars_list)))}")
        print()

    # Drift analysis
    warnings = analyze_drift(reports)
    if warnings:
        print(f"⚠ {len(warnings)} drift warning(s):\n")
        for w in warnings:
            print(f"  • {w}")
        print()
    else:
        print("✓ No env var drift detected.\n")

    if args.strict and warnings:
        sys.exit(1)


if __name__ == "__main__":
    main()
