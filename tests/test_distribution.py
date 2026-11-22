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
