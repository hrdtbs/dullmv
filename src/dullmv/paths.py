"""Project path helpers."""

from __future__ import annotations

from pathlib import Path


def find_project_root(start: Path) -> Path:
    """Return the nearest ancestor directory that contains pyproject.toml."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return current
