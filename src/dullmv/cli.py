"""Command-line interface for dullmv."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dullmv.batch import (
    default_inputs_dir,
    default_output_dir,
    discover_jobs,
    run_batch,
)
from dullmv.generator import generate


def _add_render_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "render",
        help="Generate a single music video from a DSL file",
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
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Parallel frame render workers (default: CPU count or DSL workers setting)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Print frame generation vs encoding timing breakdown",
    )


def _add_batch_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "batch",
        help="Generate videos for all image/audio pairs in inputs/",
    )
    parser.add_argument(
        "dsl_path",
        type=Path,
        help="Path to the template .dsl file",
    )
    parser.add_argument(
        "--inputs-dir",
        type=Path,
        default=None,
        help="Directory containing image/audio pairs (default: project inputs/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for rendered MP4 files (default: project outputs/)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip jobs whose output MP4 already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List discovered jobs without rendering",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue rendering remaining jobs after a failure",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dullmv",
        description="Generate music videos from effect DSL files.",
    )
    subparsers = parser.add_subparsers(dest="command")
    _add_render_parser(subparsers)
    _add_batch_parser(subparsers)
    return parser


def build_legacy_parser() -> argparse.ArgumentParser:
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
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Parallel frame render workers (default: CPU count or DSL workers setting)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Print frame generation vs encoding timing breakdown",
    )
    return parser


def _run_render(
    dsl_path: Path,
    output: Path | None,
    *,
    workers: int | None = None,
    profile: bool = False,
) -> int:
    if not dsl_path.is_file():
        print(f"Error: DSL file not found: {dsl_path}", file=sys.stderr)
        return 1
    resolved_output = output.resolve() if output else None
    generate(
        dsl_path.resolve(),
        resolved_output,
        workers=workers,
        profile=profile,
    )
    return 0


def _run_batch(args: argparse.Namespace) -> int:
    dsl_path = args.dsl_path.resolve()
    if not dsl_path.is_file():
        print(f"Error: DSL file not found: {dsl_path}", file=sys.stderr)
        return 1

    inputs_dir = (args.inputs_dir or default_inputs_dir(dsl_path)).resolve()
    output_dir = (args.output_dir or default_output_dir(dsl_path)).resolve()

    if not inputs_dir.is_dir():
        print(f"Error: inputs directory not found: {inputs_dir}", file=sys.stderr)
        return 1

    jobs, warnings = discover_jobs(inputs_dir)
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    if not jobs:
        print(f"Error: no image/audio pairs found in {inputs_dir}", file=sys.stderr)
        return 1

    print(f"Discovered {len(jobs)} job(s)")
    result = run_batch(
        dsl_path,
        jobs,
        output_dir,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
        continue_on_error=args.continue_on_error,
    )

    if args.dry_run:
        print(f"Dry run complete: {len(result.succeeded)} job(s) would be rendered.")
        return 0

    print(
        f"Batch complete: {len(result.succeeded)} succeeded, "
        f"{len(result.skipped)} skipped, {len(result.failed)} failed."
    )
    return 1 if result.failed else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and not argv[0].startswith("-") and argv[0].endswith(".dsl"):
        args = build_legacy_parser().parse_args(argv)
        return _run_render(
            args.dsl_path,
            args.output,
            workers=getattr(args, "workers", None),
            profile=getattr(args, "profile", False),
        )

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "render":
        return _run_render(
            args.dsl_path,
            args.output,
            workers=args.workers,
            profile=args.profile,
        )
    if args.command == "batch":
        return _run_batch(args)

    parser.print_help()
    return 1
