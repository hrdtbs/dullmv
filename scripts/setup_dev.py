"""Install dev dependencies and register pre-commit hooks."""

from __future__ import annotations

import subprocess
import sys


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.check_call(command)


def main() -> int:
    run(["uv", "sync", "--all-extras"])
    run(["uv", "run", "pre-commit", "install"])
    print("Dev setup complete. Ruff will run on git commit via pre-commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
