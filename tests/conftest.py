"""Shared pytest fixtures."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def minimal_dsl_text() -> str:
    return (FIXTURES_DIR / "minimal.dsl").read_text(encoding="utf-8")
