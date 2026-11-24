"""Fixtures for this pack's tests.

`scripts_dir` points at the pack's own scripts folder, so tests read the
same way they did under tests/. The core library (lib, vault) and
test_helpers are importable through pyproject's pythonpath setting.
"""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def scripts_dir():
    return Path(__file__).resolve().parent.parent / "scripts"
