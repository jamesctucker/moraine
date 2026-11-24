"""Golden tasks the quality pack contributes to the eval harness.

agent-eval.py loads this file only while the pack is enabled and runs the
TASKS it exposes — the same shape as the core GOLDEN_TASKS entries. A
core-only workspace scores 5/5; this pack adds the three slop tasks.
"""

import json
import subprocess
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parent
SLOP_CHECK = PACK_ROOT / "scripts" / "slop-check.py"
SLOP_FIXTURES = PACK_ROOT / "scripts" / "slop-fixtures"
SLOP_RULES = PACK_ROOT / "scripts" / "slop-rules"


def run_slop_fixture(name: str) -> dict | None:
    """Run slop-check on one fixture file; None if the script errors."""
    result = subprocess.run(
        [sys.executable, str(SLOP_CHECK), "--repo", str(SLOP_FIXTURES / name), "--json"],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except ValueError:
        return None


def check_slop_rules_valid() -> tuple[bool, str]:
    """Every ast-grep rule YAML parses (scan on fixtures exercises parsing)."""
    if not SLOP_RULES.is_dir():
        return False, "slop-rules/ not found"
    result = subprocess.run(
        ["ast-grep", "scan", "--config", str(SLOP_RULES / "sgconfig.yml"),
         "--json", str(SLOP_FIXTURES)],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        return False, f"ast-grep scan failed: {(result.stderr or result.stdout)[:300]}"
    return True, "all slop-rules parse and scan"


def check_slop_fixture_clean() -> tuple[bool, str]:
    """Clean fixture must stay clean — catches detector false positives."""
    snap = run_slop_fixture("clean.py")
    if snap is None:
        return False, "slop-check failed on clean.py"
    e, v = snap.get("erosion"), snap.get("verbosity")
    if e is None or v is None:
        return False, f"incomplete measurement (erosion={e}, verbosity={v})"
    if e <= 0.10 and v <= 0.05:
        return True, f"clean.py erosion {e:.3f} verbosity {v:.3f}"
    return False, f"clean.py regressed: erosion {e:.3f} (>0.10) or verbosity {v:.3f} (>0.05) — detector false positives?"


def check_slop_fixture_sloppy() -> tuple[bool, str]:
    """Sloppy fixture must stay flagged — catches detector rot."""
    snap = run_slop_fixture("sloppy.py")
    if snap is None:
        return False, "slop-check failed on sloppy.py"
    v = snap.get("verbosity")
    if v is None:
        return False, "verbosity not measured"
    if v >= 0.30:
        return True, f"sloppy.py verbosity {v:.3f} >= 0.30"
    return False, f"sloppy.py verbosity {v:.3f} < 0.30 — detectors no longer fire?"


TASKS: list[dict] = [
    {"name": "slop-rules-valid", "description": "slop-rules YAML all parse", "check": check_slop_rules_valid},
    {"name": "slop-fixture-clean", "description": "clean fixture stays clean (no detector false positives)", "check": check_slop_fixture_clean},
    {"name": "slop-fixture-sloppy", "description": "sloppy fixture stays flagged (no detector rot)", "check": check_slop_fixture_sloppy},
]
