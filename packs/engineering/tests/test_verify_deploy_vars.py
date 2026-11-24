"""Tests for scripts/workspace/verify-deploy-vars.py — --repo containment."""

import pytest
from test_helpers import load_module


@pytest.fixture
def vdv(scripts_dir, tmp_path, monkeypatch, capsys):
    module = load_module("verify_deploy_vars", scripts_dir / "verify-deploy-vars.py")
    module.WORK_DIR = tmp_path / "repos"
    module.WORK_DIR.mkdir()
    (module.WORK_DIR / "my-app").mkdir()
    return module


def run_main(vdv, argv):
    """Run main() and return its exit behavior: the exit code, or None."""
    vdv.sys.argv = ["verify-deploy-vars.py", *argv]
    try:
        vdv.main()
    except SystemExit as e:
        return e.code
    return None


class TestRepoContainment:
    def test_plain_repo_name_is_accepted(self, vdv, capsys):
        assert run_main(vdv, ["--repo", "my-app"]) is None
        assert "Scanning 1 repo(s)" in capsys.readouterr().out

    def test_absolute_path_rejected(self, vdv, tmp_path):
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        (outside / ".env").write_text("SECRET=1\n")
        assert run_main(vdv, ["--repo", str(outside)]) == 1
        assert not list(outside.rglob("*.yml"))

    def test_traversal_rejected(self, vdv):
        assert run_main(vdv, ["--repo", "../elsewhere"]) == 1
        assert run_main(vdv, ["--repo", ".."]) == 1
        assert run_main(vdv, ["--repo", "."]) == 1

    def test_nested_path_rejected(self, vdv):
        assert run_main(vdv, ["--repo", "my-app/config"]) == 1
