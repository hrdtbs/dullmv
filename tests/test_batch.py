"""Tests for batch job discovery and execution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from dullmv.batch import discover_jobs, run_batch


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


@pytest.fixture
def inputs_tree(tmp_path: Path) -> Path:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()

    track_a = inputs_dir / "track_a"
    track_a.mkdir()
    _touch(track_a / "cover.png")
    _touch(track_a / "mix.wav")

    track_b = inputs_dir / "track_b"
    track_b.mkdir()
    _touch(track_b / "art.jpg")
    _touch(track_b / "final.mp3")

    ambiguous = inputs_dir / "ambiguous"
    ambiguous.mkdir()
    _touch(ambiguous / "a.png")
    _touch(ambiguous / "b.png")
    _touch(ambiguous / "audio.wav")

    return inputs_dir


def test_discover_subfolder_jobs(inputs_tree: Path) -> None:
    jobs, warnings = discover_jobs(inputs_tree, layout="subfolder")

    assert len(jobs) == 2
    assert {job.name for job in jobs} == {"track_a", "track_b"}
    assert any("ambiguous" in warning for warning in warnings)


def test_discover_flat_jobs(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    _touch(inputs_dir / "song01.png")
    _touch(inputs_dir / "song01.wav")
    _touch(inputs_dir / "song02.jpg")
    _touch(inputs_dir / "song02.flac")

    jobs, warnings = discover_jobs(inputs_dir, layout="flat")

    assert len(jobs) == 2
    assert {job.name for job in jobs} == {"song01", "song02"}
    assert warnings == []


def test_discover_auto_prefers_subfolder(inputs_tree: Path) -> None:
    jobs, _warnings = discover_jobs(inputs_tree, layout="auto")

    assert len(jobs) == 2
    assert {job.name for job in jobs} == {"track_a", "track_b"}


def test_discover_auto_falls_back_to_flat(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    _touch(inputs_dir / "one.png")
    _touch(inputs_dir / "one.wav")

    jobs, warnings = discover_jobs(inputs_dir, layout="auto")

    assert len(jobs) == 1
    assert jobs[0].name == "one"
    assert warnings == []


def test_run_batch_dry_run(tmp_path: Path, inputs_tree: Path) -> None:
    dsl_path = tmp_path / "template.dsl"
    dsl_path.write_text("size 640 360\n", encoding="utf-8")
    output_dir = tmp_path / "outputs"

    jobs, _warnings = discover_jobs(inputs_tree, layout="subfolder")
    result = run_batch(
        dsl_path,
        jobs,
        output_dir,
        dry_run=True,
    )

    assert len(result.succeeded) == 2
    assert result.skipped == []
    assert result.failed == []
    assert not any(output_dir.iterdir())


def test_run_batch_skip_existing(tmp_path: Path, inputs_tree: Path) -> None:
    dsl_path = tmp_path / "template.dsl"
    dsl_path.write_text("size 640 360\n", encoding="utf-8")
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    (output_dir / "track_a.mp4").write_bytes(b"existing")

    jobs, _warnings = discover_jobs(inputs_tree, layout="subfolder")
    with patch("dullmv.batch.generate") as generate_mock:
        result = run_batch(
            dsl_path,
            jobs,
            output_dir,
            skip_existing=True,
        )

    assert len(result.skipped) == 1
    assert result.skipped[0][0].name == "track_a"
    assert generate_mock.call_count == 1
    assert generate_mock.call_args.kwargs["base_image"].name == "art.jpg"


def test_discover_unknown_layout_raises(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()

    with pytest.raises(ValueError, match="Unknown layout"):
        discover_jobs(inputs_dir, layout="invalid")
