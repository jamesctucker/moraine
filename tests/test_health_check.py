"""Tests for scripts/workspace/health-check.py."""

import json

import pytest
from test_helpers import load_module


@pytest.fixture
def hc(scripts_dir):
    return load_module("health_check", scripts_dir / "health-check.py")


def write_config(tmp_path, config):
    """Write an opencode.json fixture; caller points the checker at it."""
    config_path = tmp_path / "opencode.json"
    config_path.write_text(json.dumps(config))
    return config_path


class TestRun:
    def test_successful_command(self, hc):
        rc, stdout, stderr = hc.run(["echo", "hello"])
        assert rc == 0
        assert stdout == "hello"

    def test_failing_command(self, hc):
        rc, stdout, stderr = hc.run(["false"])
        assert rc != 0

    def test_missing_command(self, hc):
        rc, stdout, stderr = hc.run(["this-command-does-not-exist-12345"])
        assert rc != 0
        assert "not found" in stderr.lower() or rc == 127


class TestCheckGit:
    def test_git_found(self, hc):
        result = hc.check_git()
        assert result["tool"] == "git"
        assert result["status"] == "ok"


class TestCheckPython:
    def test_python_found(self, hc):
        result = hc.check_python()
        assert result["tool"] == "python"
        assert result["status"] == "ok"
        assert "version" in result["details"]


class TestCheckNode:
    def test_node_found(self, hc):
        result = hc.check_node()
        assert result["tool"] == "node"


class TestCheckMcpServers:
    def test_no_config(self, hc, tmp_path):
        hc.OPECODE_CONFIG = tmp_path / "nonexistent.json"
        results = hc.check_mcp_servers()
        assert len(results) == 1
        assert results[0]["status"] == "error"

    def test_invalid_config(self, hc, tmp_path):
        config_path = tmp_path / "opencode.json"
        config_path.write_text("not json")
        hc.OPECODE_CONFIG = config_path
        results = hc.check_mcp_servers()
        assert results[0]["status"] == "error"

    def test_real_config_inspects_actual_servers(self, hc):
        """The repo's real opencode.json: iterate mcp.servers, not mcp itself."""
        results = hc.check_mcp_servers()
        tools = {r["tool"] for r in results}
        assert tools == {"mcp/semble", "mcp/headroom"}
        # Shape errors on the real config are never OK; a missing binary on
        # PATH is environment-dependent and only ever a warn.
        assert all(r["status"] in ("ok", "warn") for r in results)
        for r in results:
            assert r["details"].get("command"), f"{r['tool']} lost its command"

    def test_flat_mcp_without_servers_is_error(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(
            tmp_path, {"mcp": {"semble": {"type": "local", "command": ["uvx"]}}})
        results = hc.check_mcp_servers()
        assert len(results) == 1
        assert results[0]["status"] == "error"
        assert "servers" in results[0]["details"]["error"]

    def test_mcp_not_a_mapping_is_error(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(tmp_path, {"mcp": ["semble"]})
        results = hc.check_mcp_servers()
        assert results[0]["status"] == "error"

    def test_servers_not_a_mapping_is_error(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(tmp_path, {"mcp": {"servers": ["semble"]}})
        results = hc.check_mcp_servers()
        assert results[0]["status"] == "error"
        assert "servers" in results[0]["details"]["error"]

    def test_empty_servers_mapping_is_warn(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(tmp_path, {"mcp": {"servers": {}}})
        results = hc.check_mcp_servers()
        assert results[0]["status"] == "warn"

    def test_missing_mcp_key_is_warn(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(tmp_path, {})
        results = hc.check_mcp_servers()
        assert results[0]["status"] == "warn"

    def test_server_entry_not_a_mapping_is_error(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(tmp_path, {"mcp": {"servers": {"x": "local"}}})
        results = hc.check_mcp_servers()
        assert results[0]["status"] == "error"
        assert "mapping" in results[0]["details"]["error"]

    def test_local_command_resolves(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(
            tmp_path, {"mcp": {"servers": {"x": {"type": "local", "command": ["/bin/echo", "hi"]}}}})
        result = hc.check_mcp_servers()[0]
        assert result["status"] == "ok"
        assert result["details"]["command"] == "/bin/echo hi"
        assert "not started" in result["details"]["note"]

    def test_local_executable_missing_from_path_is_warn(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(
            tmp_path, {"mcp": {"servers": {"x": {"type": "local",
                                                 "command": ["no-such-binary-xyz"]}}}})
        result = hc.check_mcp_servers()[0]
        assert result["status"] == "warn"
        assert "PATH" in result["details"]["warning"]

    def test_local_command_wrong_shape_is_error(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(
            tmp_path, {"mcp": {"servers": {"x": {"type": "local", "command": "uvx"}}}})
        result = hc.check_mcp_servers()[0]
        assert result["status"] == "error"
        assert "command" in result["details"]["error"]

    def test_remote_url_listed_without_probe(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(
            tmp_path, {"mcp": {"servers": {"x": {"type": "remote",
                                                 "url": "https://example.com/mcp"}}}})
        result = hc.check_mcp_servers()[0]
        assert result["status"] == "ok"
        assert result["details"]["url"] == "https://example.com/mcp"
        assert "not probed" in result["details"]["note"]

    def test_remote_missing_url_is_error(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(
            tmp_path, {"mcp": {"servers": {"x": {"type": "remote"}}}})
        result = hc.check_mcp_servers()[0]
        assert result["status"] == "error"
        assert "url" in result["details"]["error"]

    def test_unknown_server_type_is_error(self, hc, tmp_path):
        hc.OPECODE_CONFIG = write_config(
            tmp_path, {"mcp": {"servers": {"x": {"type": "carrier-pigeon"}}}})
        result = hc.check_mcp_servers()[0]
        assert result["status"] == "error"
        assert "carrier-pigeon" in result["details"]["error"]


class TestWriteReport:
    def test_writes_report(self, hc, tmp_path):
        hc.STAGING_DIR = tmp_path
        checks = [
            {"tool": "git", "status": "ok", "details": {"version": "2.40"}},
            {"tool": "python", "status": "warn", "details": {"warning": "old"}},
        ]
        report_path = hc.write_report(checks, quick=True)
        assert report_path.exists()
        content = report_path.read_text()
        assert "Health Check" in content
        assert "git" in content
        assert "ok" in content
        assert "warn" in content
