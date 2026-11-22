"""Release-scope and third-party distribution checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".opencode" / "skills"

THIRD_PARTY_SKILLS = (
    "agent/retro",
    "design/impeccable",
    "engineering/code-review",
    "engineering/diagnose",
    "engineering/domain-modeling",
    "engineering/executing-plans",
    "engineering/improve-codebase-architecture",
    "engineering/prototype",
    "engineering/tdd",
    "engineering/wayfinder",
    "engineering/wizard",
    "engineering/writing-plans",
    "productivity/brainstorming",
    "productivity/grilling",
    "productivity/humanize",
    "productivity/teach",
    "productivity/to-questionnaire",
)


def test_removed_release_blockers_stay_out_of_the_tree():
    removed = (
        SKILLS / "productivity" / "pdf",
        ROOT / "scripts" / "sandbox" / "opencode-sandbox",
        ROOT / "scripts" / "sandbox" / "pii-scan",
    )

    assert all(not path.exists() for path in removed)


def test_third_party_skills_carry_their_license():
    missing = [
        skill
        for skill in THIRD_PARTY_SKILLS
        if not any((SKILLS / skill / filename).is_file() for filename in ("LICENSE", "LICENSE.txt"))
    ]

    assert not missing, f"Missing bundled license files: {missing}"


def test_impeccable_embedded_components_carry_their_license():
    impeccable = SKILLS / "design" / "impeccable"

    assert (impeccable / "NOTICE.md").is_file()
    assert (impeccable / "scripts" / "modern-screenshot.LICENSE.txt").is_file()
    assert (impeccable / "reference" / "typecraft-guide-skill.LICENSE.txt").is_file()


def test_adoption_surface_files_exist():
    expected = (
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "CODE_OF_CONDUCT.md",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md",
        ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
    )
    missing = [str(p.relative_to(ROOT)) for p in expected if not p.is_file()]
    assert not missing, f"Missing community/adoption files: {missing}"


def test_employer_data_boundary_is_documented():
    # The required boundary statement plus the scanning-is-a-backstop caveat
    # must stay in both the README and AGENTS.md.
    for doc in (ROOT / "README.md", ROOT / "AGENTS.md"):
        content = doc.read_text(encoding="utf-8")
        assert "Moraine is for personal workspaces" in content, f"{doc.name} lost the employer-data boundary"
        assert "backstop" in content, f"{doc.name} lost the scanning-backstop caveat"
