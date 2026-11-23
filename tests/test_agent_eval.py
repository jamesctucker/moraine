"""Tests for scripts/workspace/agent-eval.py."""

import pytest
from test_helpers import build_workspace, load_module


@pytest.fixture
def ev(scripts_dir):
    return load_module("agent_eval", scripts_dir / "agent-eval.py")


class TestCheckSessionSearch:
    def test_passes_with_structured_results(self, ev):
        passed, detail = ev.check_session_search()
        assert passed, detail
        assert "structured" in detail

    def test_rejects_no_match_response(self, ev, monkeypatch):
        """A query that matches nothing must fail explicitly, never pass
        on the strength of nonempty output alone."""
        monkeypatch.setattr(
            ev, "FIXTURE_SESSION",
            "# 2026-01-15: Quiet session\n\n## Notes\nNothing to see here.\n")
        monkeypatch.setattr(
            ev, "FIXTURE_STAGING",
            "# Staging — 2026-01-16\n\n- an unremarkable note\n")
        passed, detail = ev.check_session_search()
        assert not passed
        assert "no-match" in detail

    def test_missing_index_script(self, ev, monkeypatch):
        monkeypatch.setattr(ev, "SESSIONS_INDEX", ev.WORKSPACE / "scripts" / "workspace" / "nope.py")
        passed, detail = ev.check_session_search()
        assert not passed
        assert "not found" in detail


class TestPackTasks:
    def _eval_module(self, workspace, pack):
        source = (
            f'TASKS = [{{"name": "{pack}-task", "description": "d",\n'
            '          "check": lambda: (True, "ok")}]\n'
        )
        (workspace / "packs" / pack / "eval.py").write_text(source)

    def test_no_tasks_when_no_enabled_pack_ships_eval(self, ev, tmp_path, monkeypatch):
        workspace = build_workspace(tmp_path, packs={"demo": {"skills": ["alpha"]}})
        monkeypatch.setattr(ev, "WORKSPACE", workspace)

        assert ev.pack_tasks() == []

    def test_loads_tasks_from_an_enabled_pack(self, ev, tmp_path, monkeypatch):
        listing = "version: 1\nharnesses: [opencode]\npacks: [demo]\n"
        workspace = build_workspace(tmp_path, listing, packs={"demo": {"skills": ["alpha"]}})
        self._eval_module(workspace, "demo")
        monkeypatch.setattr(ev, "WORKSPACE", workspace)

        tasks = ev.pack_tasks()

        assert [t["name"] for t in tasks] == ["demo-task"]
        assert tasks[0]["check"]() == (True, "ok")

    def test_ignores_eval_in_a_disabled_pack(self, ev, tmp_path, monkeypatch):
        workspace = build_workspace(tmp_path, packs={"demo": {"skills": ["alpha"]}})
        self._eval_module(workspace, "demo")
        monkeypatch.setattr(ev, "WORKSPACE", workspace)

        assert ev.pack_tasks() == []


class TestWriteResults:
    def test_writes_all_task_rows(self, ev, tmp_path, monkeypatch):
        monkeypatch.setattr(ev, "RESULTS_DIR", tmp_path)
        results = [
            {"name": f"task-{i}", "description": "d", "passed": True, "detail": "ok"}
            for i in range(8)
        ]
        path = ev.write_results(results)
        text = path.read_text()
        assert "**Score:** 8/8 (100% pass)" in text
        assert "task-0" in text
        assert "task-7" in text
