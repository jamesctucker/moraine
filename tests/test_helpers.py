"""Shared test utilities — import is stable because module name doesn't collide with conftest."""

import importlib.util
import sys


def load_module(name, filepath):
    """Load a Python module even if the filename contains hyphens."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {filepath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PACK_YAML = "name: {name}\ndescription: The {name} pack.\n"
CORE_SKILLS = ("session-handoff", "session-search")


def build_workspace(root, manifest="version: 1\nharnesses: [opencode]\npacks: []\nmcp: {}\n", packs=None):
    """A throwaway Moraine workspace: moraine.yaml, core skills, and packs with skills.

    `packs` maps a pack name to {"yaml": pack.yaml text, "skills": [ids],
    "jobs": [file names in jobs/]}; the yaml defaults to a minimal valid one.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "moraine.yaml").write_text(manifest)
    skills = root / ".agents" / "skills"
    skills.mkdir(parents=True)
    for skill_id in CORE_SKILLS:
        _write_skill(skills / skill_id, skill_id)
    for name, spec in (packs or {}).items():
        pack = root / "packs" / name
        pack.mkdir(parents=True)
        (pack / "pack.yaml").write_text(spec.get("yaml", PACK_YAML.format(name=name)))
        for skill_id in spec.get("skills", ()):
            _write_skill(pack / "skills" / skill_id, skill_id)
        for job in spec.get("jobs", ()):
            (pack / "jobs").mkdir(exist_ok=True)
            (pack / "jobs" / job).write_text("name: job\ncron: \"0 8 * * 1\"\nprompt: test\n")
    return root


def _write_skill(folder, skill_id):
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {skill_id}\ndescription: The {skill_id} skill.\n---\nBody\n")
