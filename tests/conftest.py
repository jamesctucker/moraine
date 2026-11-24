"""Shared pytest fixtures for workspace tests."""

import sys
import tempfile
from pathlib import Path

import pytest

# Ensure tests/ and scripts/workspace/ are on sys.path so test_helpers and
# intra-module imports (e.g. frontmatter) can be resolved.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "workspace"))


@pytest.fixture(scope="session")
def scripts_dir():
    return Path(__file__).resolve().parent.parent / "scripts" / "workspace"


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
