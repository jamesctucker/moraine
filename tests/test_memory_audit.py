"""Tests for scripts/workspace/memory-audit.py."""

import sys
from datetime import date

import pytest
from test_helpers import load_module

TODAY = date(2026, 9, 2)


@pytest.fixture
def ma(scripts_dir):
    return load_module("memory_audit", scripts_dir / "memory-audit.py")


@pytest.fixture
def fake_scripts(ma, tmp_path, monkeypatch):
    """Point WORKSPACE_SCRIPTS at an empty dir tests fill with fake scripts."""
    root = tmp_path / "fake-scripts"
    root.mkdir()
    monkeypatch.setattr(ma, "WORKSPACE_SCRIPTS", root)
    return root


STALE_ROW = "Active  Old Project   medium  2026-05-01  120d  *STALE*"


class TestExtractDates:
    def test_iso_dates(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        assert ma.extract_dates("due by 2026-08-27 please", TODAY) == [date(2026, 8, 27)]

    def test_month_name_dates(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        assert ma.extract_dates("installation Tuesday Sept 8", TODAY) == [date(2026, 9, 8)]

    def test_month_name_with_suffix(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        assert ma.extract_dates("ship it Sept 8th, review Aug 31st", TODAY) == [
            date(2026, 9, 8),
            date(2026, 8, 31),
        ]

    def test_month_name_wraps_year_forward(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        # "Jan 5" in September should mean January of the following year.
        assert ma.extract_dates("revisit Jan 5", TODAY) == [date(2027, 1, 5)]

    def test_month_name_wraps_year_backward(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        # "Dec 25" in January should mean December of the prior year.
        assert ma.extract_dates("shipped Dec 25", date(2026, 1, 10)) == [date(2025, 12, 25)]

    def test_dedupes(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        assert ma.extract_dates("2026-08-27 and again 2026-08-27", TODAY) == [
            date(2026, 8, 27)
        ]

    def test_ignores_invalid_month_day(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        assert ma.extract_dates("on Feb 30 or Apr 31", TODAY) == []

    def test_no_dates(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        assert ma.extract_dates("no dates here, just words", TODAY) == []


class TestOpenThreadBullets:
    CONTENT = """# Memory Index

## Active projects

- **Foo** — active

## Open threads

- **Thread one**: follow up by 2026-08-27, details at `path/`.
  more detail lines
- **Thread two** — no dates at all

## Recent decisions (2026-08-31)

- Did a thing.
"""

    def test_extracts_only_open_threads_section(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        bullets = ma.open_thread_bullets(self.CONTENT)
        assert len(bullets) == 2
        assert bullets[0].startswith("**Thread one**")
        assert "more detail lines" in bullets[0]  # continuation joined
        assert bullets[1].startswith("**Thread two**")


class TestStaleThreads:
    CONTENT = """## Open threads

- **Past due**: follow up by 2026-08-27 (promise made).
- **Future deadline**: installation Sept 8, run through the list.
- **Dateless thread**: keep an eye on marketplace fees.
- **Mixed dates**: started 2026-06-15, next step due 2026-09-10.
"""

    def test_flags_only_threads_whose_latest_date_is_old(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        stale = ma.stale_threads(self.CONTENT, TODAY, stale_days=5)
        assert len(stale) == 1
        assert stale[0].preview.startswith("**Past due**")
        assert stale[0].latest == date(2026, 8, 27)

    def test_dateless_and_future_dated_threads_ignored(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        stale = ma.stale_threads(self.CONTENT, TODAY, stale_days=0)
        previews = " ".join(t.preview for t in stale)
        assert "Dateless" not in previews
        assert "Future deadline" not in previews

    def test_threshold_respected(self, scripts_dir):
        ma = load_module("memory_audit", scripts_dir / "memory-audit.py")
        # exactly 6 days old with a 7-day threshold → not stale
        assert ma.stale_threads(
            "## Open threads\n- Task: done by 2026-08-27.\n", TODAY, stale_days=7
        ) == []


class TestDelegatedScripts:
    """Child failures must surface as findings, never as clean results."""

    def test_failing_prune_reported_not_clean(self, ma, fake_scripts):
        (fake_scripts / "prune-decisions.py").write_text(
            "import sys\n"
            "sys.stderr.write('Traceback (most recent call last):\\n"
            "ModuleNotFoundError: No module named yaml\\n')\n"
            "sys.exit(1)\n"
        )
        rows, err = ma.prune_candidates()
        assert rows == []
        assert "prune-decisions.py" in err
        assert "exit 1" in err
        assert "ModuleNotFoundError" in err

    def test_missing_script_reported_not_clean(self, ma, fake_scripts):
        rows, err = ma.prune_candidates()
        assert rows == []
        assert err is not None
        assert "prune-decisions.py" in err

    def test_failing_registry_reported_not_clean(self, ma, fake_scripts):
        (fake_scripts / "validate-repos.py").write_text("import sys\nsys.exit(2)\n")
        issues, err = ma.repo_registry_issues()
        assert issues == []
        assert "validate-repos.py" in err
        assert "exit 2" in err

    def test_stalled_projects_parsed_from_output(self, ma, fake_scripts):
        (fake_scripts / "project-status.py").write_text(f"print('{STALE_ROW}')\n")
        rows, err = ma.stalled_projects(7)
        assert err is None
        assert rows == ["Old Project (Active)"]

    def test_stalled_projects_child_failure_reported(self, ma, fake_scripts):
        (fake_scripts / "project-status.py").write_text("import sys\nsys.exit(3)\n")
        rows, err = ma.stalled_projects(7)
        assert rows == []
        assert "project-status.py" in err


class TestBuildReport:
    def _patch_workspace(self, ma, tmp_path, monkeypatch):
        monkeypatch.setattr(ma, "INDEX", tmp_path / "index.md")
        (tmp_path / "index.md").write_text("## Open threads\n- nothing pending\n")
        for dirname in ("sessions", "reviews", "staging"):
            monkeypatch.setattr(ma, f"{dirname.upper()}_DIR", tmp_path / dirname)
            (tmp_path / dirname).mkdir()

    def test_child_failure_and_stalled_counted_while_exit_stays_zero(
        self, ma, fake_scripts, tmp_path, monkeypatch, capsys
    ):
        (fake_scripts / "prune-decisions.py").write_text("import sys\nsys.exit(1)\n")
        (fake_scripts / "validate-repos.py").write_text("print('ok')\n")
        (fake_scripts / "project-status.py").write_text(f"print('{STALE_ROW}')\n")
        self._patch_workspace(ma, tmp_path, monkeypatch)

        monkeypatch.setattr(sys, "argv", ["memory-audit.py", "--days", "7"])
        with pytest.raises(SystemExit) as exc:
            ma.main()
        assert exc.value.code == 0

        out = capsys.readouterr().out
        assert "audit unavailable" in out
        assert "Old Project" in out
        assert "Nothing needs attention" not in out

    def test_clean_workspace_reports_nothing_to_attention(
        self, ma, fake_scripts, tmp_path, monkeypatch, capsys
    ):
        (fake_scripts / "prune-decisions.py").write_text("print('No candidate blocks found.')\n")
        (fake_scripts / "validate-repos.py").write_text("print('ok')\n")
        (fake_scripts / "project-status.py").write_text(
            "print('All Active/Paused projects have session activity.')\n"
        )
        self._patch_workspace(ma, tmp_path, monkeypatch)
        review = tmp_path / "reviews" / f"{date.today().isoformat()}-weekly.md"
        review.write_text("review\n")

        monkeypatch.setattr(sys, "argv", ["memory-audit.py", "--days", "7"])
        with pytest.raises(SystemExit) as exc:
            ma.main()
        assert exc.value.code == 0

        out = capsys.readouterr().out
        assert "Nothing needs attention" in out
