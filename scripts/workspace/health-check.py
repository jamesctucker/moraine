#!/usr/bin/env python3
"""Agent health check — validates that core tools are available before a session.

Validates:
  1. git installed and repo is clean-ish
  2. python3 available with required packages
  3. MCP servers in opencode.json — 'mcp.servers' shape validated; local
     commands resolved on PATH. Servers are never started and remote URLs
     are never probed, so this is not a reachability or handshake check.
  4. sync drift — the sync plan runs in dry-run mode and any difference is
     flagged with the command that fixes it; manifest or sync problems are
     errors. Runs in --quick mode too.

Writes a summary to memory/staging/health-check-{YYYY-MM-DD}.md.

Usage:
  python scripts/workspace/health-check.py          # full check
  python scripts/workspace/health-check.py --quick  # skip MCP server checks
"""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import sync
from lib import WORKSPACE
from manifest import ManifestError

STAGING_DIR = WORKSPACE / "memory" / "staging"
OPECODE_CONFIG = WORKSPACE / ".opencode" / "opencode.json"


def run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"


def check_git() -> dict:
    """Check git is installed and the repo is functional."""
    result = {"tool": "git", "status": "ok", "details": {}}

    rc, stdout, stderr = run(["git", "--version"])
    if rc != 0:
        result["status"] = "error"
        result["details"]["error"] = stderr
        return result
    result["details"]["version"] = stdout

    rc, stdout, stderr = run(["git", "rev-parse", "--show-toplevel"])
    if rc != 0:
        result["status"] = "error"
        result["details"]["error"] = "not a git repository"
    else:
        result["details"]["repo_root"] = stdout

    rc, stdout, stderr = run(["git", "status", "--porcelain"])
    if rc == 0:
        lines = [line for line in stdout.split("\n") if line.strip()]
        result["details"]["uncommitted_changes"] = len(lines)

    return result


def check_python() -> dict:
    """Check python3 is available and the running interpreter has the packages.

    Import checks use sys.executable — the interpreter running this health
    check is the one that runs the workspace scripts, and it may be the
    .venv python while a bare `python3` on PATH has nothing installed.
    """
    result = {"tool": "python", "status": "ok", "details": {}}

    rc, stdout, stderr = run(["python3", "--version"])
    if rc != 0:
        result["status"] = "error"
        result["details"]["error"] = stderr
        return result
    result["details"]["version"] = stdout

    # Check key packages available
    for pkg in ("yaml", "sqlite3", "pathlib"):
        rc, _, stderr = run([sys.executable, "-c", f"import {pkg}"])
        if rc != 0:
            result["status"] = "warn"
            result["details"].setdefault("missing_packages", []).append(pkg)

    return result


def _check_local_mcp(name: str, command: object) -> dict:
    entry = {"tool": f"mcp/{name}", "status": "ok", "details": {}}
    if not (isinstance(command, list) and command and all(isinstance(part, str) for part in command)):
        entry["status"] = "error"
        entry["details"]["error"] = "local server needs a non-empty 'command' list of strings"
        return entry

    entry["details"]["command"] = " ".join(command)
    first = command[0]
    rc, _, _ = run(["which", first] if not first.startswith(("/", ".")) else ["test", "-x", first])
    if rc != 0:
        entry["status"] = "warn"
        entry["details"]["warning"] = f"executable '{first}' not found on PATH"
    else:
        entry["details"]["note"] = "command resolves on PATH (server not started)"
    return entry


def _check_mcp_server(name: str, server: object) -> dict:
    if not isinstance(server, dict):
        return {
            "tool": f"mcp/{name}",
            "status": "error",
            "details": {"error": f"server config must be a mapping, got {type(server).__name__}"},
        }

    server_type = server.get("type")
    if server_type == "local":
        return _check_local_mcp(name, server.get("command"))

    entry = {"tool": f"mcp/{name}", "status": "ok", "details": {}}
    if server_type == "remote":
        url = server.get("url")
        if not isinstance(url, str) or not url:
            entry["status"] = "error"
            entry["details"]["error"] = "remote server needs a 'url' string"
        else:
            entry["details"]["url"] = url
            entry["details"]["note"] = "remote — URL not probed (no network check)"
    else:
        entry["status"] = "error"
        entry["details"]["error"] = f"unknown server type: {server_type!r}"
    return entry


def check_mcp_servers() -> list[dict]:
    """Check MCP servers from opencode.json's 'mcp.servers' mapping."""
    if not OPECODE_CONFIG.is_file():
        return [{"tool": "mcp_config", "status": "error", "details": {"error": "opencode.json not found"}}]

    try:
        config = json.loads(OPECODE_CONFIG.read_text())
    except json.JSONDecodeError as e:
        return [{"tool": "mcp_config", "status": "error", "details": {"error": f"invalid JSON: {e}"}}]

    mcp = config.get("mcp")
    if not mcp:
        return [{"tool": "mcp_servers", "status": "warn", "details": {"warning": "no MCP servers configured"}}]
    if not isinstance(mcp, dict):
        return [{"tool": "mcp_servers", "status": "error",
                 "details": {"error": f"'mcp' must be a mapping, got {type(mcp).__name__}"}}]

    servers = mcp.get("servers")
    if not isinstance(servers, dict):
        return [{"tool": "mcp_servers", "status": "error",
                 "details": {"error": "'mcp' config has no 'servers' mapping (expected one entry per server)"}}]
    if not servers:
        return [{"tool": "mcp_servers", "status": "warn", "details": {"warning": "no MCP servers configured"}}]

    return [_check_mcp_server(name, server) for name, server in servers.items()]


def check_sync() -> dict:
    """Run the sync plan in dry-run mode and flag any difference."""
    result = {"tool": "sync", "status": "ok", "details": {}}
    try:
        pending = sync.plan(WORKSPACE).changes
    except (ManifestError, sync.SyncError) as e:
        result["status"] = "error"
        result["details"]["error"] = "; ".join(e.problems)
        return result
    if pending:
        result["status"] = "warn"
        result["details"]["warning"] = f"{len(pending)} change(s) pending; run: python3 scripts/moraine sync"
    else:
        result["details"]["note"] = "workspace matches moraine.yaml"
    return result


def write_report(checks: list[dict], quick: bool) -> Path:
    """Write health-check summary to staging."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    ok_count = sum(1 for c in checks if c.get("status") == "ok")
    warn_count = sum(1 for c in checks if c.get("status") == "warn")
    error_count = sum(1 for c in checks if c.get("status") == "error")

    lines = [
        f"# Health Check — {today}",
        "",
        f"**Run at:** {timestamp}",
        f"**Mode:** {'quick' if quick else 'full'}",
        f"**Results:** {ok_count} ok, {warn_count} warn, {error_count} error",
        "",
        "| Tool | Status | Details |",
        "|------|--------|---------|",
    ]

    for c in checks:
        status = c["status"]
        details = ", ".join(f"{k}={v}" for k, v in c.get("details", {}).items())
        lines.append(f"| {c['tool']} | {status} | {details} |")

    lines.append("")

    report_path = STAGING_DIR / f"health-check-{today}.md"
    report_path.write_text("\n".join(lines) + "\n")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent health check for workspace startup.")
    parser.add_argument("--quick", "-q", action="store_true", help="Skip MCP server checks")
    args = parser.parse_args()

    print("=== Workspace — Agent Health Check ===\n")

    checks = []

    # Core tools and sync drift (sync runs in quick mode too: it is cheap
    # and the manifests gate everything else)
    for check_fn, label in [(check_git, "git"), (check_python, "python"), (check_sync, "sync")]:
        result = check_fn()
        checks.append(result)
        icon = {"ok": "OK", "warn": "WARN", "error": "FAIL"}.get(result["status"], "?")
        print(f"  [{icon}] {label}")

    # MCP servers
    if not args.quick:
        mcp_results = check_mcp_servers()
        checks.extend(mcp_results)
        for r in mcp_results:
            icon = {"ok": "OK", "warn": "WARN", "error": "FAIL"}.get(r["status"], "?")
            print(f"  [{icon}] {r['tool']}")

    # Write report
    report_path = write_report(checks, args.quick)
    print(f"\nReport written to: {report_path.relative_to(WORKSPACE)}")

    error_count = sum(1 for c in checks if c.get("status") == "error")
    if error_count > 0:
        print(f"\n{error_count} check(s) failed. Review the report before starting a session.")
        return 1

    print("\nHealth check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
