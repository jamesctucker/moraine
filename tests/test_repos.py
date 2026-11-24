"""Tests for scripts/workspace/repos.py — the repos/ pointer registry."""

import os
import subprocess

import pytest
from test_helpers import load_module


def run_git(*args, cwd=None):
    """git without inherited GIT_* env. When the suite runs inside a hook or
    rebase, GIT_DIR points at the caller's repository and redirects these
    commands there — `-C` does not override it — corrupting that repo
    instead of building the fixture in tmp_path."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True)


@pytest.fixture
def rp(scripts_dir):
    return load_module("repos", scripts_dir / "repos.py")


def registry(workspace, text):
    """Write repos/README.md; returns its path."""
    path = workspace / "repos" / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


REPOS_TABLE = """# /repos

## Repos

| Repo | What it is | Path | Remote | Hint |
|------|------------|------|--------|------|
| storefront | Next.js app | repos/storefront | git@github.com:acme/storefront.git | Read its AGENTS.md first |
| payments | Payments service | repos/payments | git@github.com:acme/payments.git | |
"""

AREAS_TABLE = """# /repos

## Areas

| Area | Covers | File |
|------|--------|------|
| Billing | invoices, payments, tax | repos/billing.md |
"""


class TestParsing:
    def test_reads_a_repos_table(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE)

        repos, problems = rp.load_registry(tmp_path)

        assert not problems
        assert [(r.name, r.path, r.remote, r.hint) for r in repos] == [
            ("storefront", "repos/storefront", "git@github.com:acme/storefront.git", "Read its AGENTS.md first"),
            ("payments", "repos/payments", "git@github.com:acme/payments.git", ""),
        ]

    def test_the_optional_machines_column_is_read(self, rp, tmp_path):
        table = with_machines(
            REPOS_TABLE,
            "| storefront | Next.js app | repos/storefront | git@github.com:acme/storefront.git | Read its AGENTS.md first |",
            "| storefront | Next.js app | repos/storefront | git@github.com:acme/storefront.git | | big-box, laptop |",
        )
        registry(tmp_path, table)

        repos, _ = rp.load_registry(tmp_path)

        assert repos[0].machines == ("big-box", "laptop")
        assert repos[1].machines == ()

    def test_area_files_hold_their_own_repos_tables(self, rp, tmp_path):
        registry(tmp_path, AREAS_TABLE)
        (tmp_path / "repos" / "billing.md").write_text(
            REPOS_TABLE.replace("payments", "invoices").replace("payments.git", "invoices.git")
        )

        repos, problems = rp.load_registry(tmp_path)

        assert not problems
        assert [r.name for r in repos] == ["storefront", "invoices"]

    def test_a_missing_area_file_is_a_problem(self, rp, tmp_path):
        registry(tmp_path, AREAS_TABLE)

        _, problems = rp.load_registry(tmp_path)

        assert any("billing.md" in problem for problem in problems)

    def test_a_file_with_both_kinds_of_table_is_a_problem(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE + "\n" + AREAS_TABLE)

        _, problems = rp.load_registry(tmp_path)

        assert any("both a Repos table and an Areas table" in problem for problem in problems)

    def test_a_missing_readme_is_a_problem(self, rp, tmp_path):
        repos, problems = rp.load_registry(tmp_path)

        assert repos == []
        assert any("not found" in problem for problem in problems)

    def test_unrelated_tables_are_left_alone(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE + """
| TODO | When |
|------|------|
| thing | someday |
""")

        repos, problems = rp.load_registry(tmp_path)

        assert not problems
        assert len(repos) == 2


class TestRegistryRules:
    def test_a_repo_listed_twice_is_a_problem(self, rp, tmp_path):
        registry(tmp_path, """# /repos

## Areas

| Area | Covers | File |
|------|--------|------|
| Billing | invoices, payments | repos/billing.md |
| Other | everything else | repos/other.md |
""")
        (tmp_path / "repos" / "billing.md").write_text(REPOS_TABLE)
        (tmp_path / "repos" / "other.md").write_text(REPOS_TABLE)

        repos, _ = rp.load_registry(tmp_path)
        findings = rp.registry_problems(repos)

        assert any("'storefront' is listed in both" in problem for problem in findings)

    def test_a_missing_remote_is_a_problem(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE.replace("git@github.com:acme/payments.git", ""))

        repos, _ = rp.load_registry(tmp_path)
        findings = rp.registry_problems(repos)

        assert any("'payments' has no Remote" in finding for finding in findings)

    def test_absolute_or_escaping_paths_are_problems(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE.replace("repos/payments", "../elsewhere"))

        repos, _ = rp.load_registry(tmp_path)
        findings = rp.registry_problems(repos)

        assert any("must be relative or start with ~/" in finding for finding in findings)


class TestMachines:
    def test_no_machines_column_means_every_machine(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE)
        repos, _ = rp.load_registry(tmp_path)

        assert all(rp.on_this_machine(repo, host="anything") for repo in repos)

    def test_machine_entries_scope_to_matching_hostnames(self, rp, tmp_path):
        table = with_machines(
            REPOS_TABLE,
            "| storefront | Next.js app | repos/storefront | git@github.com:acme/storefront.git | Read its AGENTS.md first |",
            "| storefront | Next.js app | repos/storefront | git@github.com:acme/storefront.git | | big-box |",
        )
        registry(tmp_path, table)
        repos, _ = rp.load_registry(tmp_path)
        storefront = next(r for r in repos if r.name == "storefront")

        assert rp.on_this_machine(storefront, host="big-box")
        assert not rp.on_this_machine(storefront, host="laptop")


def clone(workspace, name, remote):
    """A real local git repo with an origin, so origin() has something to read."""
    path = workspace / "repos" / name
    path.mkdir(parents=True)
    run_git("init", "-q", str(path))
    run_git("-C", str(path), "remote", "add", "origin", remote)
    return path


def with_machines(table, row_old, row_new):
    """Give a table the Machines column and swap one row for a scoped one."""
    return table.replace(
        "| Repo | What it is | Path | Remote | Hint |\n|------|------------|------|--------|------|",
        "| Repo | What it is | Path | Remote | Hint | Machines |\n"
        "|------|------------|------|--------|------|---------|",
    ).replace(row_old, row_new)


class TestCheck:
    def test_clean_registry_matches_disk(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE)
        clone(tmp_path, "storefront", "git@github.com:acme/storefront.git")
        clone(tmp_path, "payments", "git@github.com:acme/payments.git")

        assert rp.check(tmp_path, host="laptop") == []

    def test_a_missing_repo_is_flagged_with_the_fix(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE)

        findings = rp.check(tmp_path, host="laptop")

        assert any("'storefront'" in f and "moraine repos restore" in f for f in findings)

    def test_a_repo_scoped_to_another_machine_is_not_missing_here(self, rp, tmp_path):
        table = with_machines(
            REPOS_TABLE,
            "| storefront | Next.js app | repos/storefront | git@github.com:acme/storefront.git | Read its AGENTS.md first |",
            "| storefront | Next.js app | repos/storefront | git@github.com:acme/storefront.git | | big-box |",
        )
        registry(tmp_path, table)
        clone(tmp_path, "payments", "git@github.com:acme/payments.git")

        assert rp.check(tmp_path, host="laptop") == []

    def test_an_unregistered_clone_is_flagged(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE)
        stray = tmp_path / "repos" / "stray"
        (stray / ".git").mkdir(parents=True)

        findings = rp.check(tmp_path, host="laptop")

        assert any("unregistered clone: repos/stray" in f for f in findings)

    def test_a_remote_mismatch_is_flagged(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE)
        repo = tmp_path / "repos" / "storefront"
        repo.mkdir()
        run_git("init", "-q", str(repo))
        run_git("-C", str(repo), "remote", "add", "origin", "git@github.com:wrong/storefront.git")

        findings = rp.check(tmp_path, host="laptop")

        assert any("remote drift" in f and "wrong/storefront" in f for f in findings)


class TestRestore:
    def test_missing_repos_for_this_machine(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE)
        (tmp_path / "repos" / "storefront").mkdir()  # payments stays missing

        missing = rp.missing_repos(tmp_path, host="laptop")

        assert [r.name for r in missing] == ["payments"]

    def test_rows_without_a_remote_are_not_restore_candidates(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE.replace("git@github.com:acme/payments.git", ""))

        missing = rp.missing_repos(tmp_path, host="laptop")

        assert [r.name for r in missing] == ["storefront"]

    def test_clone_command_construction(self, rp, tmp_path):
        registry(tmp_path, REPOS_TABLE)
        repo = rp.missing_repos(tmp_path, host="laptop")[0]

        command = rp.clone_command(tmp_path, repo)

        assert command == ["git", "clone", repo.remote, str(tmp_path / "repos" / "storefront")]


class TestCli:
    def test_check_prints_findings_and_stays_flag_only(self, rp, tmp_path, capsys):
        registry(tmp_path, REPOS_TABLE)

        assert rp.main(["check"], workspace=tmp_path) == 0

        out = capsys.readouterr().out
        assert "moraine repos restore" in out
        assert "finding(s)" in out
