"""End-to-end CapCut template render pipeline."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dullmv.capcut.config import load_config
from dullmv.capcut.draft import apply_template
from dullmv.paths import find_project_root


@dataclass
class ProfileStats:
    draft_sec: float = 0.0
    export_sec: float = 0.0

    def print_summary(self) -> None:
        total = self.draft_sec + self.export_sec
        print(
            f"Timing: draft {self.draft_sec:.1f}s, "
            f"export {self.export_sec:.1f}s, total {total:.1f}s"
        )


def default_output_path(config_path: Path, job_name: str | None = None) -> Path:
    root = find_project_root(config_path.parent)
    stem = job_name or config_path.stem
    return root / "outputs" / f"{stem}.mp4"


def render(
    config_path: Path,
    out_path: Path,
    *,
    job_name: str,
    image: Path | str,
    audio: Path | str,
    profile: bool = False,
    skip_export: bool = False,
) -> Path:
    """Build a CapCut draft from a template and export an MP4."""
    config = load_config(config_path.resolve())
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    stats = ProfileStats()
    draft_started = time.perf_counter()
    draft_name, _script = apply_template(
        config,
        job_name=job_name,
        image_path=Path(image),
        audio_path=Path(audio),
    )
    stats.draft_sec = time.perf_counter() - draft_started
    print(f"Draft ready: {draft_name}")

    if skip_export:
        if profile:
            stats.print_summary()
        return out_path

    if sys.platform != "win32":
        raise RuntimeError("CapCut export requires Windows with CapCut desktop installed")

    from dullmv.capcut.export import (
        CapCutController,
        resolve_framerate,
        resolve_resolution,
    )

    export_started = time.perf_counter()
    controller = CapCutController()
    controller.export_draft(
        draft_name,
        out_path,
        resolution=resolve_resolution(config.export.resolution),
        framerate=resolve_framerate(config.export.framerate),
        timeout=config.export.timeout_sec,
    )
    stats.export_sec = time.perf_counter() - export_started

    if profile:
        stats.print_summary()

    return out_path
