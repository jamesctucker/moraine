"""Release-scope and third-party distribution checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_SKILLS = ROOT / ".agents" / "skills"
PACK_SKILLS = ROOT / "packs"

# `<owner>/<id>`: core skills sit in .agents/skills, the rest in their pack.
THIRD_PARTY_SKILLS = (
    ".agents/grilling",
    ".agents/domain-modeling",
    "engineering/code-review",
    "engineering/diagnose",
    "engineering/executing-plans",
    "engineering/improve-codebase-architecture",
    "engineering/prototype",
    "engineering/tdd",
    "engineering/wayfinder",
    "engineering/wizard",
    "engineering/writing-plans",
    "reflection/retro",
    "writing/brainstorming",
    "writing/humanize",
    "writing/teach",
    "writing/to-questionnaire",
)


def skill_path(skill: str) -> Path:
    """Resolve a THIRD_PARTY_SKILLS entry to its skill folder."""
    owner, skill_id = skill.split("/")
    if owner == ".agents":
        return CORE_SKILLS / skill_id
    return PACK_SKILLS / owner / "skills" / skill_id


def test_removed_release_blockers_stay_out_of_the_tree():
    removed = (
        PACK_SKILLS / "writing" / "skills" / "pdf",
        ROOT / "scripts" / "sandbox" / "opencode-sandbox",
        ROOT / "scripts" / "sandbox" / "pii-scan",
    )

    assert all(not path.exists() for path in removed)


def test_skills_are_core_folders_or_packed():
    """Flat layout: core skills are real folders in .agents/skills and every
    other shipped skill lives in packs/<pack>/skills/<id>/."""
    core = {path.name for path in CORE_SKILLS.iterdir() if path.is_dir() and not path.is_symlink()}
    packed = {path.name for path in PACK_SKILLS.glob("*/skills/*")}

    assert not (ROOT / ".opencode" / "skills").exists()
    assert core == {
        "create-skill", "domain-modeling", "grilling", "scaffold-project",
        "session-handoff", "session-search", "sync-upstream",
    }
    assert not core & packed


def test_third_party_skills_carry_their_license():
    missing = [
        skill
        for skill in THIRD_PARTY_SKILLS
        if not any((skill_path(skill) / filename).is_file() for filename in ("LICENSE", "LICENSE.txt"))
    ]

    assert not missing, f"Missing bundled license files: {missing}"


def test_impeccable_embedded_components_carry_their_license():
    impeccable = skill_path("design/impeccable")

    assert (impeccable / "NOTICE.md").is_file()
    assert (impeccable / "scripts" / "modern-screenshot.LICENSE.txt").is_file()
    assert (impeccable / "reference" / "typecraft-guide-skill.LICENSE.txt").is_file()


def test_adoption_surface_files_exist():
    expected = (
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
