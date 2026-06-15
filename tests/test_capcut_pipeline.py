"""Tests for CapCut render pipeline."""

from __future__ import annotations

import sys
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

    controller_instance = MagicMock()
    mock_export = MagicMock()
    mock_export.CapCutController = MagicMock(return_value=controller_instance)
    mock_export.resolve_resolution = MagicMock(return_value=None)
    mock_export.resolve_framerate = MagicMock(return_value=None)

    with (
        patch("dullmv.capcut.pipeline.apply_template", return_value=("dullmv_demo", MagicMock())),
        patch("dullmv.capcut.pipeline.sys.platform", "win32"),
        patch.dict(sys.modules, {"dullmv.capcut.export": mock_export}),
    ):
        render(
            config_path,
            output,
            job_name="demo",
            image=image,
            audio=audio,
        )

    controller_instance.export_draft.assert_called_once()
