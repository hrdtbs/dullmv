"""YAML configuration for CapCut template rendering."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class TextSlot(BaseModel):
    segment_index: int = Field(ge=0)
    content: str
    track_index: int = Field(default=0, ge=0)
    track_name: str | None = None


class SlotsConfig(BaseModel):
    image: str
    audio: str
    texts: list[TextSlot] = Field(default_factory=list)


class ExportConfig(BaseModel):
    resolution: Literal["8K", "4K", "2K", "1080P", "720P", "480P"] | None = "1080P"
    framerate: Literal[24, 25, 30, 50, 60] | None = 30
    timeout_sec: float = Field(default=1200, gt=0)


class TemplateConfig(BaseModel):
    drafts_dir: Path
    template_name: str
    output_draft_prefix: str = "dullmv_"
    slots: SlotsConfig
    export: ExportConfig = Field(default_factory=ExportConfig)

    @field_validator("drafts_dir", mode="before")
    @classmethod
    def _expand_drafts_dir(cls, value: object) -> object:
        if isinstance(value, str):
            expanded = os.path.expandvars(value)
            return Path(expanded).expanduser()
        return value


def load_config(path: Path) -> TemplateConfig:
    """Load and validate a template YAML file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config file (expected mapping): {path}")

    env_drafts_dir = os.environ.get("CAPCUT_DRAFTS_DIR")
    if env_drafts_dir and "drafts_dir" not in data:
        data["drafts_dir"] = env_drafts_dir
    elif env_drafts_dir:
        data["drafts_dir"] = env_drafts_dir

    return TemplateConfig.model_validate(data)
