"""Command-line interface for dullmv."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dullmv.generator import generate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dullmv",
        description="Generate a music video from an effect DSL file.",
    )
    parser.add_argument(
        "dsl_path",
        type=Path,
        help="Path to the .dsl file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output MP4 path (default: outputs/<dsl-stem>.mp4 under project root)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dsl_path = args.dsl_path.resolve()
    if not dsl_path.is_file():
        print(f"Error: DSL file not found: {dsl_path}", file=sys.stderr)
        return 1
    output = args.output.resolve() if args.output else None
    generate(dsl_path, output)
    return 0
