#!/usr/bin/env python3
"""Agent Evaluation Harness — golden task set for agentic quality.

Runs a suite of golden tasks that the workspace agent should complete
correctly. Each task has a deterministic check. Results are recorded
to memory/eval/results/ for weekly pass/fail tracking.

Core tasks live here. A pack may contribute its own golden tasks by
shipping an eval.py that exposes TASKS; those run only while the pack
is enabled, so a core-only workspace is not penalized for them.

Usage:
  python scripts/workspace/agent-eval.py           # run all tasks
  python scripts/workspace/agent-eval.py --verbose  # detailed output
  python scripts/workspace/agent-eval.py --history  # show last 12 weeks
"""

import argparse
import contextlib
import importlib.util
import io
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from lib import WORKSPACE
from manifest import enabled_packs, load_manifests, local_pack

RESULTS_DIR = WORKSPACE / "memory" / "eval" / "results"
SESSIONS_INDEX = WORKSPACE / "scripts" / "workspace" / "session-index.py"
VALIDATE_SCRIPT = WORKSPACE / "scripts" / "workspace" / "validate.py"

# Known session-search fixture: indexed in a temp dir by check_session_search
# so the golden task is deterministic on a fresh clone (where memory/sessions/
# holds only READMEs and no index exists yet).
FIXTURE_QUERY = "evalfixture"
FIXTURE_DATES = {"2026-01-15", "2026-01-16"}
FIXTURE_SESSION = """# 2026-01-15: Eval fixture session

## Notes
Indexed a known evalfixture session so the session-search golden task is
deterministic on a fresh clone, where no real index exists yet.

## Decisions
- The session-search golden task builds its own small index fixture.
"""
FIXTURE_STAGING = """# Staging — 2026-01-16

- evalfixture staging note covers the memory/staging half of the index.
"""


def pack_tasks() -> list[dict]:
    """Golden tasks contributed by enabled packs.

    The core harness names no pack: it loads packs/<name>/eval.py for each
    enabled pack (plus the local one) and runs the TASKS list it exposes.
    """
    manifest, packs = load_manifests(WORKSPACE)
    enabled = enabled_packs(manifest.packs, packs)
    tasks: list[dict] = []
    for pack in (local_pack(WORKSPACE), *enabled.values()):
        module_path = pack.path / "eval.py"
        if not module_path.is_file():
            continue
        spec = importlib.util.spec_from_file_location(f"pack_eval_{pack.name}", module_path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tasks.extend(getattr(module, "TASKS", []))
    return tasks


def check_license() -> tuple[bool, str]:
    license_path = WORKSPACE / "LICENSE"
    if not license_path.is_file():
        return False, "LICENSE file not found"
    text = license_path.read_text()
    if "MIT" in text:
        return True, "LICENSE found with MIT text"
    return False, "LICENSE found but does not contain MIT"


def check_validate_script() -> tuple[bool, str]:
    if not VALIDATE_SCRIPT.is_file():
        return False, f"validate.py not found at {VALIDATE_SCRIPT.relative_to(WORKSPACE)}"
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--quiet"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        return True, "validate.py passed"
    errors = result.stderr.strip() or result.stdout.strip()
    return False, f"validate.py failed:\n{errors[:500]}"


def check_session_search() -> tuple[bool, str]:
    """session-index.py builds and searches a small known index fixture.

    Fresh-clone safe: on a new clone memory/sessions/ holds only READMEs and
    no index exists, so the check builds its own fixture in a temp dir instead
    of depending on workspace state. A no-match response is an explicit
    failure, and results must be structured rows — not merely nonempty output.
    """
    if not SESSIONS_INDEX.is_file():
        return False, f"session-index.py not found at {SESSIONS_INDEX.relative_to(WORKSPACE)}"

    spec = importlib.util.spec_from_file_location("session_index_fixture", SESSIONS_INDEX)
    if spec is None or spec.loader is None:
        return False, "could not load session-index.py as a module"
    index = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(index)

    with tempfile.TemporaryDirectory() as tmp:
        sessions_dir = Path(tmp) / "sessions"
        staging_dir = Path(tmp) / "staging"
        sessions_dir.mkdir()
        staging_dir.mkdir()
        (sessions_dir / "2026-01-15-eval-fixture.md").write_text(FIXTURE_SESSION, encoding="utf-8")
        (staging_dir / "2026-01-16-eval-fixture.md").write_text(FIXTURE_STAGING, encoding="utf-8")

        index.SESSIONS_DIR = sessions_dir
        index.STAGING_DIR = staging_dir
        index.DB_DIR = Path(tmp) / "index"
        index.DB_PATH = index.DB_DIR / "sessions.db"

        with contextlib.redirect_stdout(io.StringIO()):
            index.rebuild_index()
        results = index.search_index(FIXTURE_QUERY, limit=5)

    if not results:
        return False, f"no-match response for '{FIXTURE_QUERY}' — the known fixture must match"
    missing_keys = [k for k in ("date", "title", "snippet", "section", "project_links")
                    if k not in results[0]]
    if missing_keys:
        return False, f"unstructured results (missing keys: {', '.join(missing_keys)})"
    dates = {r["date"] for r in results}
    if dates != FIXTURE_DATES:
        return False, f"fixture not fully indexed: matched dates {sorted(dates)}, expected {sorted(FIXTURE_DATES)}"
    return True, f"built a 2-file fixture index; search returned {len(results)} structured results for '{FIXTURE_QUERY}'"


def check_gitattributes() -> tuple[bool, str]:
    path = WORKSPACE / ".gitattributes"
    if not path.is_file():
        return False, ".gitattributes not found"
    return True, ".gitattributes found"


def check_editorconfig() -> tuple[bool, str]:
    path = WORKSPACE / ".editorconfig"
    if not path.is_file():
        return False, ".editorconfig not found"
    return True, ".editorconfig found"


GOLDEN_TASKS: list[dict] = [
    {"name": "license-exists", "description": "LICENSE exists with MIT text", "check": check_license},
    {"name": "validate-passes", "description": "validate.py exits 0", "check": check_validate_script},
    {"name": "session-search-works", "description": "session-index.py builds and searches a known fixture", "check": check_session_search},
    {"name": "gitattributes-exists", "description": ".gitattributes exists", "check": check_gitattributes},
    {"name": "editorconfig-exists", "description": ".editorconfig exists", "check": check_editorconfig},
]


def get_week_tag(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(UTC)
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def run_all_tasks(verbose: bool) -> list[dict]:
    results: list[dict] = []
    print("=== Agent Evaluation Harness ===\n")
    tasks = [*GOLDEN_TASKS, *pack_tasks()]
    for task in tasks:
        name = task["name"]
        try:
            passed, detail = task["check"]()
        except Exception as e:
            passed, detail = False, str(e)
        results.append({
            "name": name,
            "description": task["description"],
            "passed": passed,
            "detail": detail,
        })
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}")
        if verbose or not passed:
            print(f"         {detail}")
    return results


def write_results(results: list[dict]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    week = get_week_tag(now)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    results_path = RESULTS_DIR / f"{week}.md"
    lines = [
        f"# Agent Eval — {week}",
        "",
        f"**Run at:** {now.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"**Score:** {passed}/{total} ({passed / total * 100:.0f}% pass)",
        "",
        "| Task | Status | Detail |",
        "|------|--------|--------|",
    ]
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        detail = r["detail"].replace("\n", " ").strip()
        lines.append(f"| {r['name']} | {status} | {detail} |")
    lines.append("")

    results_path.write_text("\n".join(lines) + "\n")
    return results_path


def show_history(weeks: int = 12) -> None:
    if not RESULTS_DIR.is_dir():
        print("No eval history found.")
        return
    files = sorted(RESULTS_DIR.glob("*-W*.md"), reverse=True)[:weeks]
    if not files:
        print("No eval history found.")
        return
    print(f"=== Eval History (last {len(files)} weeks) ===\n")
    print(f"{'Week':<16} {'Score':<10} {'Trend':<10}")
    print("-" * 36)
    scores: list[tuple[str, float]] = []
    for f in files:
        text = f.read_text()
        m = re.search(r"\*\*Score:\*\* (\d+)/(\d+)", text)
        if m:
            pct = int(m.group(1)) / int(m.group(2)) * 100
            scores.append((f.stem, pct))
    for i, (week, pct) in enumerate(scores):
        trend = "↑" if i > 0 and pct > scores[i - 1][1] else ("↓" if i > 0 and pct < scores[i - 1][1] else "→")
        print(f"{week:<16} {pct:>5.0f}%      {trend:<10}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent golden task evaluator.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Detailed output")
    parser.add_argument("--history", action="store_true", help="Show eval history")
    args = parser.parse_args()

    if args.history:
        show_history()
        return 0

    results = run_all_tasks(args.verbose)
    report_path = write_results(results)
    print(f"\nResults: {report_path.relative_to(WORKSPACE)}")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"Score: {passed}/{total} ({passed / total * 100:.0f}% pass)")

    if passed < total:
        failing = [r["name"] for r in results if not r["passed"]]
        print(f"Failed tasks: {', '.join(failing)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
