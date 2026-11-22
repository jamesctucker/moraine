"""Behavior tests for the pre-push safety gate."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".husky" / "pre-push"


def run_hook(path: str, cwd: Path):
    env = os.environ.copy()
    env["PATH"] = path
    env.pop("SKIP_HOOKS", None)
    env.pop("EVAL_DEPS", None)
    return subprocess.run([str(HOOK)], cwd=cwd, env=env, capture_output=True, text=True, check=False)


def test_pre_push_fails_closed_when_required_tools_are_missing(tmp_path):
    result = run_hook("/nonexistent", tmp_path)

    assert result.returncode == 1
    assert "pytest not installed" in result.stdout
    assert "ruff not installed" in result.stdout
    assert "bun not installed" in result.stdout
    assert "All pre-push checks passed" not in result.stdout


def test_pre_push_has_an_explicit_acknowledged_skip(tmp_path):
    env = os.environ.copy()
    env["PATH"] = "/nonexistent"
    env["SKIP_HOOKS"] = "1"

    result = subprocess.run([str(HOOK)], cwd=tmp_path, env=env, capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert "SKIP_HOOKS set" in result.stdout
