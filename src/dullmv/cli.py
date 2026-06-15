"""Command-line interface for dullmv."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dullmv.batch import (
    BatchJob,
    default_inputs_dir,
    default_output_dir,
    discover_jobs,
    run_batch,
)
from dullmv.capcut.pipeline import default_output_path, render


def _add_render_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "render",
        help="Generate a single music video from a CapCut template config",
    )
    parser.add_argument(
        "config_path",
        type=Path,
        help="Path to the template .yaml file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output MP4 path (default: outputs/<job-name>.mp4)",
    )
    parser.add_argument(
        "--image",
        type=Path,
        default=None,
        help="Cover image path (default: single pair in inputs/)",
    )
    parser.add_argument(
        "--audio",
        type=Path,
        default=None,
        help="Audio path (default: single pair in inputs/)",
    )
    parser.add_argument(
        "--job-name",
        type=str,
        default=None,
        help="Draft/output name stem (default: image stem or config stem)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Print draft vs export timing breakdown",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Build the CapCut draft only; do not run desktop export",
    )


def _add_batch_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "batch",
        help="Generate videos for all image/audio pairs in inputs/",
    )
    parser.add_argument(
        "config_path",
        type=Path,
        help="Path to the template .yaml file",
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
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip jobs whose output MP4 already exists (default: enabled)",
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
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Print draft vs export timing breakdown for each job",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Ignored for CapCut export (always serial); kept for CLI compatibility",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Build CapCut drafts only; do not run desktop export",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dullmv",
        description="Generate music videos from CapCut templates.",
    )
    subparsers = parser.add_subparsers(dest="command")
    _add_render_parser(subparsers)
    _add_batch_parser(subparsers)
    return parser


def _resolve_single_job(
    config_path: Path,
    image: Path | None,
    audio: Path | None,
) -> BatchJob:
    if image is not None and audio is not None:
        if image.stem != audio.stem:
            print(
                "Warning: image and audio stems differ; using image stem as job name",
                file=sys.stderr,
            )
        return BatchJob(name=image.stem, image=image.resolve(), audio=audio.resolve())

    inputs_dir = default_inputs_dir(config_path)
    jobs, warnings = discover_jobs(inputs_dir)
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    if len(jobs) != 1:
        raise SystemExit(
            "Error: provide --image and --audio, or place exactly one matching pair in inputs/"
        )
    return jobs[0]


def _run_render(args: argparse.Namespace) -> int:
    config_path = args.config_path.resolve()
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        job = _resolve_single_job(config_path, args.image, args.audio)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1

    job_name = args.job_name or job.name
    output = (args.output or default_output_path(config_path, job_name)).resolve()

    render(
        config_path,
        output,
        job_name=job_name,
        image=job.image,
        audio=job.audio,
        profile=args.profile,
        skip_export=args.skip_export,
    )
    return 0


def _run_batch(args: argparse.Namespace) -> int:
    config_path = args.config_path.resolve()
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        return 1

    inputs_dir = (args.inputs_dir or default_inputs_dir(config_path)).resolve()
    output_dir = (args.output_dir or default_output_dir(config_path)).resolve()

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
        config_path,
        jobs,
        output_dir,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
        continue_on_error=args.continue_on_error,
        profile=args.profile,
        parallel_jobs=args.jobs,
        skip_export=args.skip_export,
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
        print(
            "Error: .dsl configs are no longer supported. Use templates/*.yaml instead.",
            file=sys.stderr,
        )
        return 1

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "render":
        return _run_render(args)
    if args.command == "batch":
        return _run_batch(args)

    parser.print_help()
    return 1
