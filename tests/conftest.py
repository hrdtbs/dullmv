"""Shared pytest fixtures."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config_text() -> str:
    return (FIXTURES_DIR / "sample.yaml").read_text(encoding="utf-8")
