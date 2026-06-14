"""Tests for CapCut render pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from dullmv.capcut.pipeline import render


def test_render_skip_export(tmp_path: Path, sample_config_text: str) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(sample_config_text, encoding="utf-8")

    image = tmp_path / "cover.png"
    audio = tmp_path / "bgm.wav"
    image.write_bytes(b"img")
    audio.write_bytes(b"aud")
    output = tmp_path / "out.mp4"

    with patch("dullmv.capcut.pipeline.apply_template", return_value=("dullmv_demo", MagicMock())):
        result = render(
            config_path,
            output,
            job_name="demo",
            image=image,
            audio=audio,
            skip_export=True,
        )

    assert result == output


def test_render_calls_export(tmp_path: Path, sample_config_text: str) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(sample_config_text, encoding="utf-8")

    image = tmp_path / "cover.png"
    audio = tmp_path / "bgm.wav"
    image.write_bytes(b"img")
    audio.write_bytes(b"aud")
    output = tmp_path / "out.mp4"

    with (
        patch("dullmv.capcut.pipeline.apply_template", return_value=("dullmv_demo", MagicMock())),
        patch("dullmv.capcut.export.CapCutController") as controller_cls,
    ):
        render(
            config_path,
            output,
            job_name="demo",
            image=image,
            audio=audio,
        )

    controller_cls.return_value.export_draft.assert_called_once()
