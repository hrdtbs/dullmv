"""Batch video generation from image/audio pairs."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from dullmv.generator import find_project_root, generate

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


@dataclass(frozen=True)
class BatchJob:
    name: str
    image: Path
    audio: Path

    @property
    def output_name(self) -> str:
        return f"{self.name}.mp4"


@dataclass
class BatchResult:
    succeeded: list[BatchJob] = field(default_factory=list)
    skipped: list[tuple[BatchJob, str]] = field(default_factory=list)
    failed: list[tuple[BatchJob, str]] = field(default_factory=list)


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def _is_audio(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def discover_jobs(inputs_dir: Path) -> tuple[list[BatchJob], list[str]]:
    """Discover image/audio pairs by matching file stems in inputs_dir."""
    inputs_dir = inputs_dir.resolve()
    jobs: list[BatchJob] = []
    warnings: list[str] = []

    if not inputs_dir.is_dir():
        return jobs, warnings

    images_by_stem: dict[str, Path] = {}
    audios_by_stem: dict[str, Path] = {}

    for path in sorted(inputs_dir.iterdir()):
        if not path.is_file():
            if path.is_dir():
                warnings.append(f"Ignoring subdirectory: {path.name}")
            continue
        stem = path.stem
        if _is_image(path):
            if stem in images_by_stem:
                warnings.append(f"Skipping duplicate image stem: {path.name}")
            else:
                images_by_stem[stem] = path
        elif _is_audio(path):
            if stem in audios_by_stem:
                warnings.append(f"Skipping duplicate audio stem: {path.name}")
            else:
                audios_by_stem[stem] = path

    for stem in sorted(set(images_by_stem) & set(audios_by_stem)):
        jobs.append(BatchJob(name=stem, image=images_by_stem[stem], audio=audios_by_stem[stem]))

    return jobs, warnings


def run_batch(
    dsl_path: Path,
    jobs: list[BatchJob],
    output_dir: Path,
    *,
    skip_existing: bool = False,
    dry_run: bool = False,
    continue_on_error: bool = False,
) -> BatchResult:
    dsl_path = dsl_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    result = BatchResult()

    for index, job in enumerate(jobs, start=1):
        out_path = output_dir / job.output_name
        print(f"[{index}/{len(jobs)}] {job.name}")
        print(f"  image: {job.image}")
        print(f"  audio: {job.audio}")
        print(f"  output: {out_path}")

        if skip_existing and out_path.is_file():
            reason = "output already exists"
            print(f"  skipped: {reason}")
            result.skipped.append((job, reason))
            continue

        if dry_run:
            result.succeeded.append(job)
            continue

        try:
            generate(
                dsl_path,
                out_path,
                base_image=job.image,
                audio=job.audio,
            )
            result.succeeded.append(job)
        except Exception as exc:
            message = str(exc)
            print(f"  failed: {message}", file=sys.stderr)
            result.failed.append((job, message))
            if not continue_on_error:
                break

    return result


def default_inputs_dir(dsl_path: Path) -> Path:
    return find_project_root(dsl_path.parent) / "inputs"


def default_output_dir(dsl_path: Path) -> Path:
    return find_project_root(dsl_path.parent) / "outputs"
