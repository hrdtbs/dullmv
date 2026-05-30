"""Batch video generation from image/audio pairs."""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    workers: int | None = None,
    profile: bool = False,
    parallel_jobs: int = 1,
) -> BatchResult:
    dsl_path = dsl_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    result = BatchResult()
    parallel_jobs = max(1, parallel_jobs)

    def _resolve_workers() -> int | None:
        if workers is not None:
            return workers
        if parallel_jobs > 1:
            return max(1, (os.cpu_count() or 1) // parallel_jobs)
        return None

    def _render_job(index: int, job: BatchJob) -> tuple[BatchJob, str | None, str | None]:
        out_path = output_dir / job.output_name
        print(f"[{index}/{len(jobs)}] {job.name}")
        print(f"  image: {job.image}")
        print(f"  audio: {job.audio}")
        print(f"  output: {out_path}")

        if skip_existing and out_path.is_file():
            return job, "skipped", "output already exists"

        if dry_run:
            return job, "succeeded", None

        try:
            generate(
                dsl_path,
                out_path,
                base_image=job.image,
                audio=job.audio,
                workers=_resolve_workers(),
                profile=profile,
            )
            return job, "succeeded", None
        except Exception as exc:
            return job, "failed", str(exc)

    if parallel_jobs <= 1 or dry_run:
        for index, job in enumerate(jobs, start=1):
            job_result, status, message = _render_job(index, job)
            if status == "skipped":
                print(f"  skipped: {message}")
                result.skipped.append((job_result, message or ""))
            elif status == "failed":
                print(f"  failed: {message}", file=sys.stderr)
                result.failed.append((job_result, message or ""))
                if not continue_on_error:
                    break
            else:
                result.succeeded.append(job_result)
        return result

    with ThreadPoolExecutor(max_workers=parallel_jobs) as pool:
        futures = {
            pool.submit(_render_job, index, job): job for index, job in enumerate(jobs, start=1)
        }
        for future in as_completed(futures):
            job_result, status, message = future.result()
            if status == "skipped":
                print(f"  skipped: {job_result.name} ({message})")
                result.skipped.append((job_result, message or ""))
            elif status == "failed":
                print(f"  failed: {job_result.name}: {message}", file=sys.stderr)
                result.failed.append((job_result, message or ""))
                if not continue_on_error:
                    for pending in futures:
                        pending.cancel()
                    break
            else:
                result.succeeded.append(job_result)

    return result


def default_inputs_dir(dsl_path: Path) -> Path:
    return find_project_root(dsl_path.parent) / "inputs"


def default_output_dir(dsl_path: Path) -> Path:
    return find_project_root(dsl_path.parent) / "outputs"
