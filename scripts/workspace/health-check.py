#!/usr/bin/env python3
"""Agent health check — validates that core tools are available before a session.

Validates:
  1. git installed and repo is clean-ish
  2. python3 available with required packages
  3. node available with correct version
  4. MCP servers reachable (from opencode.json config)

Writes a summary to memory/staging/health-check-{YYYY-MM-DD}.md.

Usage:
  python scripts/workspace/health-check.py          # full check
  python scripts/workspace/health-check.py --quick  # skip MCP reachability
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib import WORKSPACE
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
        lines = [l for l in stdout.split("\n") if l.strip()]
        result["details"]["uncommitted_changes"] = len(lines)

    return result


def check_python() -> dict:
    """Check python3 is available and can import key modules."""
    result = {"tool": "python", "status": "ok", "details": {}}

    rc, stdout, stderr = run(["python3", "--version"])
    if rc != 0:
        result["status"] = "error"
        result["details"]["error"] = stderr
        return result
    result["details"]["version"] = stdout

    # Check key packages available
    for pkg in ("yaml", "sqlite3", "pathlib"):
        rc, _, stderr = run(["python3", "-c", f"import {pkg}"])
        if rc != 0:
            result["status"] = "warn"
            result["details"].setdefault("missing_packages", []).append(pkg)

    return result


def check_node() -> dict:
    """Check node is available and at expected version."""
    result = {"tool": "node", "status": "ok", "details": {}}

    rc, stdout, stderr = run(["node", "--version"])
    if rc != 0:
        result["status"] = "error"
        result["details"]["error"] = stderr
        return result
    result["details"]["version"] = stdout

    # Check major version >= 18
    ver = stdout.lstrip("v")
    try:
        major = int(ver.split(".")[0])
        if major < 18:
            result["status"] = "warn"
            result["details"]["warning"] = f"Node {major} < 18; consider upgrading"
    except (ValueError, IndexError):
        pass

    return result


def check_mcp_servers() -> list[dict]:
    """Check MCP servers from opencode.json config."""
    results = []

    if not OPECODE_CONFIG.is_file():
        return [{"tool": "mcp_config", "status": "error", "details": {"error": "opencode.json not found"}}]

    try:
        config = json.loads(OPECODE_CONFIG.read_text())
    except json.JSONDecodeError as e:
        return [{"tool": "mcp_config", "status": "error", "details": {"error": f"invalid JSON: {e}"}}]

    mcp = config.get("mcp", {})
    if not mcp:
        return [{"tool": "mcp_servers", "status": "warn", "details": {"warning": "no MCP servers configured"}}]

    for name, server in mcp.items():
        entry = {"tool": f"mcp/{name}", "status": "ok", "details": {}}

        if server.get("type") == "local":
            command = server.get("command", [])
            if command:
                entry["details"]["command"] = " ".join(command)
                # Quick check: can we run the first part of the command?
                first = command[0]
                rc, _, _ = run(["which", first] if not first.startswith(("/", ".")) else ["test", "-x", first])
                if rc != 0:
                    entry["status"] = "warn"
                    entry["details"]["warning"] = f"executable '{first}' not found on PATH"
        elif server.get("type") == "remote":
            url = server.get("url", "unknown")
            entry["details"]["url"] = url
            # Can't meaningfully health-check remote without curl dependency
            entry["details"]["note"] = "remote — reachability not checked (no curl dependency)"

        results.append(entry)

    return results


def write_report(checks: list[dict], quick: bool) -> Path:
    """Write health-check summary to staging."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
    parser.add_argument("--quick", "-q", action="store_true", help="Skip MCP reachability check")
    args = parser.parse_args()

    print("=== The Garage — Agent Health Check ===\n")

    checks = []

    # Core tools
    for check_fn, label in [(check_git, "git"), (check_python, "python"), (check_node, "node")]:
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
