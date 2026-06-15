"""Tests for batch job discovery and execution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from dullmv.batch import discover_jobs, run_batch


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_discover_jobs_matches_stems(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    _touch(inputs_dir / "song01.png")
    _touch(inputs_dir / "song01.wav")
    _touch(inputs_dir / "song02.jpg")
    _touch(inputs_dir / "song02.flac")

    jobs, warnings = discover_jobs(inputs_dir)

    assert len(jobs) == 2
    assert {job.name for job in jobs} == {"song01", "song02"}
    assert warnings == []


def test_discover_jobs_ignores_subdirectories(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    _touch(inputs_dir / "song01.png")
    _touch(inputs_dir / "song01.wav")

    nested = inputs_dir / "nested"
    nested.mkdir()
    _touch(nested / "cover.png")
    _touch(nested / "mix.wav")

    jobs, warnings = discover_jobs(inputs_dir)

    assert len(jobs) == 1
    assert jobs[0].name == "song01"
    assert any("Ignoring subdirectory: nested" in warning for warning in warnings)


def test_discover_jobs_skips_unpaired_stems(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    _touch(inputs_dir / "paired.png")
    _touch(inputs_dir / "paired.wav")
    _touch(inputs_dir / "image_only.png")
    _touch(inputs_dir / "audio_only.mp3")

    jobs, warnings = discover_jobs(inputs_dir)

    assert len(jobs) == 1
    assert jobs[0].name == "paired"
    assert warnings == []


def test_discover_jobs_warns_on_duplicate_stems(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    _touch(inputs_dir / "song.png")
    _touch(inputs_dir / "song.jpg")
    _touch(inputs_dir / "song.wav")

    jobs, warnings = discover_jobs(inputs_dir)

    assert len(jobs) == 1
    assert jobs[0].name == "song"
    assert any("duplicate image stem" in warning for warning in warnings)


def test_run_batch_dry_run(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    _touch(inputs_dir / "track_a.png")
    _touch(inputs_dir / "track_a.wav")
    _touch(inputs_dir / "track_b.jpg")
    _touch(inputs_dir / "track_b.mp3")

    config_path = tmp_path / "template.yaml"
    config_path.write_text("template_name: Test\n", encoding="utf-8")
    output_dir = tmp_path / "outputs"

    jobs, _warnings = discover_jobs(inputs_dir)
    result = run_batch(
        config_path,
        jobs,
        output_dir,
        dry_run=True,
    )

    assert len(result.succeeded) == 2
    assert result.skipped == []
    assert result.failed == []
    assert not output_dir.exists() or not any(output_dir.iterdir())


def test_run_batch_skip_existing_by_default(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    _touch(inputs_dir / "track_a.png")
    _touch(inputs_dir / "track_a.wav")
    _touch(inputs_dir / "track_b.jpg")
    _touch(inputs_dir / "track_b.mp3")

    config_path = tmp_path / "template.yaml"
    config_path.write_text("template_name: Test\n", encoding="utf-8")
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    (output_dir / "track_a.mp4").write_bytes(b"existing")

    jobs, _warnings = discover_jobs(inputs_dir)
    with patch("dullmv.batch.render") as render_mock:
        result = run_batch(config_path, jobs, output_dir)

    assert len(result.skipped) == 1
    assert result.skipped[0][0].name == "track_a"
    assert render_mock.call_count == 1
    assert render_mock.call_args.kwargs["image"].name == "track_b.jpg"


def test_run_batch_no_skip_existing(tmp_path: Path) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    _touch(inputs_dir / "track_a.png")
    _touch(inputs_dir / "track_a.wav")

    config_path = tmp_path / "template.yaml"
    config_path.write_text("template_name: Test\n", encoding="utf-8")
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    (output_dir / "track_a.mp4").write_bytes(b"existing")

    jobs, _warnings = discover_jobs(inputs_dir)
    with patch("dullmv.batch.render") as render_mock:
        result = run_batch(
            config_path,
            jobs,
            output_dir,
            skip_existing=False,
        )

    assert result.skipped == []
    assert render_mock.call_count == 1
