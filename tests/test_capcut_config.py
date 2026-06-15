"""Tests for CapCut template configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dullmv.capcut.config import TemplateConfig, load_config


def test_load_config_from_fixture(tmp_path: Path, sample_config_text: str) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(sample_config_text, encoding="utf-8")

    config = load_config(config_path)

    assert config.template_name == "TestTemplate"
    assert config.slots.image == "cover.png"
    assert config.slots.audio == "bgm.wav"
    assert len(config.slots.texts) == 1
    assert config.export.resolution == "1080P"


def test_load_config_env_override(tmp_path: Path, sample_config_text: str) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(sample_config_text, encoding="utf-8")

    os.environ["CAPCUT_DRAFTS_DIR"] = "D:/Custom/Drafts"
    try:
        config = load_config(config_path)
    finally:
        os.environ.pop("CAPCUT_DRAFTS_DIR", None)

    assert str(config.drafts_dir).replace("\\", "/") == "D:/Custom/Drafts"


def test_template_config_validation() -> None:
    config = TemplateConfig.model_validate(
        {
            "drafts_dir": "C:/Drafts",
            "template_name": "MV",
            "slots": {"image": "a.png", "audio": "a.wav"},
        }
    )
    assert config.export.framerate == 30
