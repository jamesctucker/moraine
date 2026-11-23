"""Tests for snapshot history, callable identity, and detector failures.

Detector and git runners are stubbed so the suite stays hermetic.
"""

import json
import subprocess
from argparse import Namespace
from datetime import date
from pathlib import Path

import pytest
from test_helpers import load_module


@pytest.fixture
def sc(scripts_dir):
    return load_module("slop_check", scripts_dir / "slop-check.py")


@pytest.fixture
def slop_dir(sc, monkeypatch, tmp_path):
    """Redirect snapshot storage (and WORKSPACE) into tmp_path."""
    monkeypatch.setattr(sc, "WORKSPACE", tmp_path)
    target = tmp_path / "memory" / "eval" / "slop"
    monkeypatch.setattr(sc, "SLOP_DIR", target)
    return target


def freeze_today(monkeypatch, sc, day: date):
    class FrozenDate(date):
        @classmethod
        def today(cls):
            return day

    monkeypatch.setattr(sc, "date", FrozenDate)


def write_snapshot(slop_dir, day, repo="work/demo", erosion=0.1, verbosity=0.1):
    d = slop_dir / "snapshots" / day
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{repo.replace('/', '__')}.json"
    p.write_text(json.dumps({"repo": repo, "erosion": erosion, "verbosity": verbosity}))
    return p


def bare_snap(repo="work/demo", erosion=0.2, verbosity=0.2):
    return {
        "repo": repo, "erosion": erosion, "verbosity": verbosity,
        "prev": None, "delta": {"erosion": None, "verbosity": None},
    }


def fake_measure(erosion=0.1):
    return {
        "callables": 3, "erosion": erosion, "verbosity": 0.05, "nloc": 100,
        "func_nloc": 80, "max_cc": 4, "cc_over_10": 0,
        "rule_hits_by_id": {}, "rule_lines": 0, "clone_lines": 0,
        "high_cc_callables": [],
    }


def stub_measurement(monkeypatch, sc, measure=None):
    monkeypatch.setattr(sc, "measure", measure or (lambda *a, **k: fake_measure()))
    monkeypatch.setattr(sc, "git_commit", lambda p: "abc1234")
    monkeypatch.setattr(sc, "tool_versions", lambda: {})


def completed(cmd, rc=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(cmd, rc, stdout=stdout, stderr=stderr)


# ------------------------------------------- 2.6: snapshot identity, baselines

class TestLinkPrev:
    def test_multiple_mondays_in_one_month(self, sc, slop_dir):
        # Old month-keyed dirs meant the later Mondays overwrote the earlier
        # ones; date-keyed dirs keep all four and link the latest earlier one.
        for day in ("2026-11-02", "2026-11-09", "2026-11-16"):
            write_snapshot(slop_dir, day)
        snap = bare_snap()
        sc.link_prev(snap, "2026-11-23")
        assert snap["prev"].endswith("snapshots/2026-11-16/work__demo.json")
        assert snap["delta"]["erosion"] == pytest.approx(0.1)

    def test_baseline_crosses_month_boundary(self, sc, slop_dir):
        write_snapshot(slop_dir, "2026-10-26")
        write_snapshot(slop_dir, "2026-11-30", erosion=0.15)
        snap = bare_snap()
        sc.link_prev(snap, "2026-12-07")
        assert snap["prev"].endswith("snapshots/2026-11-30/work__demo.json")

    def test_current_month_snapshot_is_eligible(self, sc, slop_dir):
        # The old logic only accepted earlier months, so a December run
        # linked October even when late-November snapshots existed.
        write_snapshot(slop_dir, "2026-10-26")
        write_snapshot(slop_dir, "2026-11-16", verbosity=0.12)
        snap = bare_snap()
        sc.link_prev(snap, "2026-11-23")
        assert snap["prev"].endswith("snapshots/2026-11-16/work__demo.json")
        assert snap["delta"]["verbosity"] == pytest.approx(0.08)

    def test_same_day_snapshot_is_excluded(self, sc, slop_dir):
        write_snapshot(slop_dir, "2026-11-16")
        write_snapshot(slop_dir, "2026-11-23")
        snap = bare_snap()
        sc.link_prev(snap, "2026-11-23")
        assert snap["prev"].endswith("snapshots/2026-11-16/work__demo.json")

    def test_no_earlier_snapshot_leaves_prev_null(self, sc, slop_dir):
        write_snapshot(slop_dir, "2026-11-23")
        snap = bare_snap()
        sc.link_prev(snap, "2026-11-23")
        assert snap["prev"] is None
        assert snap["delta"]["erosion"] is None

    def test_legacy_month_dirs_still_link(self, sc, slop_dir):
        # Snapshots written by the old monthly layout remain usable baselines:
        # "2026-10" sorts before every "2026-11-DD".
        write_snapshot(slop_dir, "2026-10")
        snap = bare_snap()
        sc.link_prev(snap, "2026-11-23")
        assert snap["prev"].endswith("snapshots/2026-10/work__demo.json")


class TestSameDayRerun:
    def test_mode_repo_preserves_same_day_snapshot(self, sc, slop_dir, monkeypatch, capsys):
        stub_measurement(monkeypatch, sc)
        freeze_today(monkeypatch, sc, date(2026, 11, 23))
        args = Namespace(repo="work/demo", range=None, json=False, write=True,
                         include_tests=False, replace_today=False)
        sc.mode_repo(args)
        first = slop_dir / "snapshots" / "2026-11-23" / "work__demo.json"
        assert json.loads(first.read_text())["erosion"] == 0.1

        stub_measurement(monkeypatch, sc, lambda *a, **k: fake_measure(erosion=0.4))
        sc.mode_repo(args)
        assert json.loads(first.read_text())["erosion"] == 0.1
        assert "kept existing same-day snapshot" in capsys.readouterr().out

    def test_mode_repo_replace_today_overwrites(self, sc, slop_dir, monkeypatch):
        stub_measurement(monkeypatch, sc)
        freeze_today(monkeypatch, sc, date(2026, 11, 23))
        args = Namespace(repo="work/demo", range=None, json=False, write=True,
                         include_tests=False, replace_today=False)
        sc.mode_repo(args)
        stub_measurement(monkeypatch, sc, lambda *a, **k: fake_measure(erosion=0.4))
        args.replace_today = True
        sc.mode_repo(args)
        p = slop_dir / "snapshots" / "2026-11-23" / "work__demo.json"
        assert json.loads(p.read_text())["erosion"] == 0.4

    def test_mode_all_reports_kept_snapshots(self, sc, slop_dir, monkeypatch, capsys):
        stub_measurement(monkeypatch, sc)
        freeze_today(monkeypatch, sc, date(2026, 11, 23))
        monkeypatch.setattr(sc, "discover_repos", lambda: [("work/demo", slop_dir)])
        args = Namespace(include_tests=False, write=True, json=False, replace_today=False)
        sc.mode_all(args)
        p = slop_dir / "snapshots" / "2026-11-23" / "work__demo.json"
        assert p.is_file()
        stub_measurement(monkeypatch, sc, lambda *a, **k: fake_measure(erosion=0.4))
        sc.mode_all(args)
        assert json.loads(p.read_text())["erosion"] == 0.1
        assert "kept 1 same-day snapshot(s)" in capsys.readouterr().out


# ------------------------------------------------- 3.1: identity-based CC gate

class TestNewHighCc:
    def test_replacement_counts_as_new(self, sc):
        # Net count delta is zero, but a different callable is now over CC 10.
        base = {"high_cc_callables": [["old_fn", "a.py"]]}
        head = {"high_cc_callables": [["new_fn", "a.py"]]}
        assert sc.new_high_cc(base, head) == [("new_fn", "a.py")]

    def test_removal_alone_is_not_new(self, sc):
        base = {"high_cc_callables": [["fn", "a.py"], ["other", "b.py"]]}
        head = {"high_cc_callables": [["fn", "a.py"]]}
        assert sc.new_high_cc(base, head) == []

    def test_rename_counts_as_new(self, sc):
        base = {"high_cc_callables": [["foo", "a.py"]]}
        head = {"high_cc_callables": [["bar", "a.py"]]}
        assert sc.new_high_cc(base, head) == [("bar", "a.py")]

    def test_threshold_crossing_counts_as_new(self, sc):
        base = {"high_cc_callables": []}  # the callable sat at CC <= 10
        head = {"high_cc_callables": [["fn", "a.py"]]}
        assert sc.new_high_cc(base, head) == [("fn", "a.py")]

    def test_same_name_new_path_counts_as_new(self, sc):
        base = {"high_cc_callables": [["fn", "old.py"]]}
        head = {"high_cc_callables": [["fn", "new.py"]]}
        assert sc.new_high_cc(base, head) == [("fn", "new.py")]

    def test_same_short_name_in_one_file_is_disambiguated(self, sc):
        base = {"high_cc_callables": [["Foo.__init__", "a.py"]]}
        head = {"high_cc_callables": [["Foo.__init__", "a.py"], ["Bar.__init__", "a.py"]]}
        assert sc.new_high_cc(base, head) == [("Bar.__init__", "a.py")]

    def test_unmeasurable_returns_none(self, sc):
        errored = {"error": "lizard failed or timed out"}
        assert sc.new_high_cc(errored, {"high_cc_callables": []}) is None
        assert sc.new_high_cc({"high_cc_callables": []}, errored) is None


class TestLizardIdentities:
    def test_rows_carry_name_and_normalized_path(self, sc, monkeypatch, tmp_path):
        root = tmp_path / "proj"
        (root / "sub").mkdir(parents=True)
        abs_py = root / "sub" / "bar.py"
        csv_out = (
            "10,2,50,2,12,\"f@1-12@foo.py\",\"foo.py\",\"myfunc\",\"Foo.myfunc\",1,12\n"
            f"8,12,40,1,8,\"g@1-8@{abs_py}\",\"{abs_py}\",\"other\",\"Bar.other\",1,8\n"
        )
        monkeypatch.setattr(sc, "run", lambda cmd, timeout=300: completed(cmd, 0, stdout=csv_out))
        rows = sc.lizard_callables(root, [])
        by_name = {r["name"]: r for r in rows}
        assert by_name["Foo.myfunc"]["file"] == "foo.py"
        assert by_name["Bar.other"]["file"] == "sub/bar.py"

    def test_measure_reports_high_cc_identities(self, sc, monkeypatch, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        (root / "a.py").write_text("def f():\n    pass\n")
        monkeypatch.setattr(sc, "lizard_callables", lambda p, e: [
            {"name": "f", "file": "a.py", "start": 1, "end": 2, "ccn": 12, "nloc": 10},
            {"name": "g", "file": "a.py", "start": 3, "end": 4, "ccn": 5, "nloc": 4},
        ])
        monkeypatch.setattr(sc, "astgrep_lines", lambda p: (set(), {}))
        monkeypatch.setattr(sc, "jscpd_lines", lambda p, e: set())
        m = sc.measure(root)
        assert m["high_cc_callables"] == [["f", "a.py"]]
        assert m["cc_over_10"] == 1


def make_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("x = 1\n")
    for cmd in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test",
         "commit", "-qm", "init"],
    ):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    return repo


class TestRangeGate:
    def run_range(self, sc, monkeypatch, tmp_path, base, head, fail_on_new_cc=True):
        repo = make_git_repo(tmp_path)
        results = iter([base, head])
        monkeypatch.setattr(sc, "measure", lambda *a, **k: next(results))
        args = Namespace(range="HEAD..HEAD", fail_on_new_cc=fail_on_new_cc,
                         json=False, include_tests=False)
        return sc.mode_range(args, repo, "repo")

    def test_count_neutral_replacement_fails(self, sc, monkeypatch, tmp_path, capsys):
        # cc_over_10 is 1 on both sides — the old count gate passed this.
        rc = self.run_range(
            sc, monkeypatch, tmp_path,
            {**fake_measure(), "cc_over_10": 1, "high_cc_callables": [["old_fn", "a.py"]]},
            {**fake_measure(), "cc_over_10": 1, "high_cc_callables": [["new_fn", "a.py"]]})
        assert rc == 1
        assert "new_fn" in capsys.readouterr().err

    def test_removal_only_passes(self, sc, monkeypatch, tmp_path):
        rc = self.run_range(
            sc, monkeypatch, tmp_path,
            {**fake_measure(), "high_cc_callables": [["fn", "a.py"], ["gone", "b.py"]]},
            {**fake_measure(), "high_cc_callables": [["fn", "a.py"]]})
        assert rc == 0

    def test_gate_fails_closed_when_unmeasurable(self, sc, monkeypatch, tmp_path, capsys):
        errored = {"error": "lizard failed or timed out", "erosion": None,
                   "verbosity": None, "nloc": None}
        rc = self.run_range(sc, monkeypatch, tmp_path, errored, fake_measure())
        assert rc == 1
        assert "CC gate unavailable" in capsys.readouterr().err

    def test_unmeasurable_is_advisory_when_not_blocking(self, sc, monkeypatch, tmp_path):
        errored = {"error": "lizard failed or timed out", "erosion": None,
                   "verbosity": None, "nloc": None}
        rc = self.run_range(sc, monkeypatch, tmp_path, errored, fake_measure(),
                            fail_on_new_cc=False)
        assert rc == 0


# ------------------------------------- 3.2: fail-closed detectors and git paths

class TestComputedCheckExclusions:
    def test_venv_and_node_modules_are_not_scanned(self, sc, tmp_path):
        # A checkout-local .venv must not flood the Python computed checks
        # with site-packages code (experienced as a bogus verbosity jump).
        deep = tmp_path / ".venv" / "lib" / "sitepkg" / "deep.py"
        deep.parent.mkdir(parents=True)
        deep.write_text(
            "def f(a):\n"
            "    if a:\n"
            "        if a:\n"
            "            if a:\n"
            "                if a:\n"
            "                    if a:\n"
            "                        return a\n"
        )
        (tmp_path / "clean.py").write_text("def g():\n    return 1\n")

        _, hits = sc.computed_checks(tmp_path)
        assert hits == {}

    def test_repo_files_are_still_scanned(self, sc, tmp_path):
        (tmp_path / "nested.py").write_text(
            "def f(a):\n"
            "    if a:\n"
            "        if a:\n"
            "            if a:\n"
            "                if a:\n"
            "                    if a:\n"
            "                        return a\n"
        )
        _, hits = sc.computed_checks(tmp_path)
        assert hits.get("py-deep-nesting") == 1


class TestAstgrepAvailability:
    def test_broken_rules_are_not_zero_findings(self, sc, monkeypatch):
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 2, stderr="bad rule"))
        assert sc.astgrep_lines(Path("x")) is None

    def test_clean_scan_is_empty(self, sc, monkeypatch):
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 0, stdout=""))
        assert sc.astgrep_lines(Path("x")) == (set(), {})

    def test_match_exit_code_still_parses(self, sc, monkeypatch):
        # ast-grep exits 1 on matches when a rule's severity is error.
        out = json.dumps([{"file": "a.py", "ruleId": "r",
                           "range": {"start": {"line": 0}, "end": {"line": 0}}}])
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 1, stdout=out))
        lines, hits = sc.astgrep_lines(Path("x"))
        assert ("a.py", 1) in lines
        assert hits["r"] == 1

    def test_error_exit_is_unavailable_even_with_partial_json(self, sc, monkeypatch):
        out = json.dumps([{"file": "a.py", "ruleId": "r",
                           "range": {"start": {"line": 0}, "end": {"line": 0}}}])
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 6, stdout=out, stderr="bad rule"))
        assert sc.astgrep_lines(Path("x")) is None


class TestChangedFiles:
    def test_parses_nul_separated_names(self, sc, monkeypatch):
        def fake(cmd, timeout=300):
            if "--cached" in cmd:
                return completed(cmd, 0, stdout="a.py\0my file.py\0")
            return completed(cmd, 1)
        monkeypatch.setattr(sc, "run", fake)
        assert sc.changed_files() == ["a.py", "my file.py"]

    def test_falls_back_to_head_diff_when_nothing_staged(self, sc, monkeypatch):
        def fake(cmd, timeout=300):
            if "--cached" in cmd:
                return completed(cmd, 0, stdout="")
            return completed(cmd, 0, stdout="b.py\0")
        monkeypatch.setattr(sc, "run", fake)
        assert sc.changed_files() == ["b.py"]

    def test_git_failure_is_none_not_empty(self, sc, monkeypatch):
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 128, stderr="fatal"))
        assert sc.changed_files() is None

    def test_staged_failure_does_not_fall_back_to_head(self, sc, monkeypatch):
        def fake(cmd, timeout=300):
            if "--cached" in cmd:
                return completed(cmd, 128, stderr="fatal")
            return completed(cmd, 0, stdout="b.py\0")
        monkeypatch.setattr(sc, "run", fake)
        assert sc.changed_files() is None


def stub_detectors(monkeypatch, sc, astgrep=None):
    monkeypatch.setattr(sc, "astgrep_lines", astgrep or (lambda f: (set(), {})))
    monkeypatch.setattr(sc, "computed_checks", lambda f: (set(), {}))
    monkeypatch.setattr(sc, "lizard_callables", lambda f, e: [])


class TestModeChanged:
    def test_spaced_filename_is_scanned_as_one_file(self, sc, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(sc, "WORKSPACE", tmp_path)
        (tmp_path / "my file.py").write_text("x = 1\n")
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 0, stdout="my file.py\0"))
        scanned = []

        def fake_astgrep(f):
            scanned.append(f)
            return (set(), {})

        stub_detectors(monkeypatch, sc, astgrep=fake_astgrep)
        rc = sc.mode_changed(Namespace(fail_on_new=True))
        assert rc == 0
        assert [p.name for p in scanned] == ["my file.py"]
        assert "clean: 1 changed files" in capsys.readouterr().out

    def test_git_failure_blocks(self, sc, monkeypatch, capsys):
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 128, stderr="fatal"))
        rc = sc.mode_changed(Namespace(fail_on_new=True))
        assert rc == 1
        assert "git diff failed" in capsys.readouterr().err

    def test_git_failure_advisory_exits_zero(self, sc, monkeypatch, capsys):
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 128, stderr="fatal"))
        rc = sc.mode_changed(Namespace(fail_on_new=False))
        assert rc == 0
        assert "git diff failed" in capsys.readouterr().err

    def test_detector_failure_blocks(self, sc, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(sc, "WORKSPACE", tmp_path)
        (tmp_path / "a.py").write_text("x = 1\n")
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 0, stdout="a.py\0"))
        stub_detectors(monkeypatch, sc, astgrep=lambda f: None)
        rc = sc.mode_changed(Namespace(fail_on_new=True))
        assert rc == 1
        captured = capsys.readouterr()
        assert "ast-grep" in captured.err
        assert "clean" not in captured.out

    def test_detector_failure_advisory_does_not_claim_clean(self, sc, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(sc, "WORKSPACE", tmp_path)
        (tmp_path / "a.py").write_text("x = 1\n")
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 0, stdout="a.py\0"))
        stub_detectors(monkeypatch, sc, astgrep=lambda f: None)
        rc = sc.mode_changed(Namespace(fail_on_new=False))
        assert rc == 0
        assert "clean" not in capsys.readouterr().out

    def test_lizard_failure_blocks_changed_mode(self, sc, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(sc, "WORKSPACE", tmp_path)
        (tmp_path / "a.py").write_text("x = 1\n")
        monkeypatch.setattr(sc, "run",
                            lambda cmd, timeout=300: completed(cmd, 0, stdout="a.py\0"))
        stub_detectors(monkeypatch, sc)
        monkeypatch.setattr(sc, "lizard_callables", lambda f, e: None)
        rc = sc.mode_changed(Namespace(fail_on_new=True))
        assert rc == 1
        assert "clean" not in capsys.readouterr().out
