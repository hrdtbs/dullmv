"""CapCut draft creation from templates using pycapcut."""

from __future__ import annotations

import shutil
from pathlib import Path

import pycapcut as cc

from dullmv.capcut.config import TemplateConfig


def build_draft_name(config: TemplateConfig, job_name: str) -> str:
    return f"{config.output_draft_prefix}{job_name}"


def draft_content_path(config: TemplateConfig, draft_name: str) -> Path:
    return config.drafts_dir / draft_name / "draft_content.json"


def apply_template(
    config: TemplateConfig,
    *,
    job_name: str,
    image_path: Path,
    audio_path: Path,
    allow_replace: bool = True,
) -> tuple[str, cc.ScriptFile]:
    """Duplicate a CapCut template draft and replace slot materials."""
    image_path = image_path.resolve()
    audio_path = audio_path.resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    drafts_dir = config.drafts_dir.resolve()
    if not drafts_dir.is_dir():
        raise FileNotFoundError(f"CapCut drafts directory not found: {drafts_dir}")

    folder = cc.DraftFolder(str(drafts_dir))
    if not folder.has_draft(config.template_name):
        raise FileNotFoundError(
            f"Template draft '{config.template_name}' not found in {drafts_dir}"
        )

    draft_name = build_draft_name(config, job_name)
    script = folder.duplicate_as_template(
        config.template_name,
        draft_name,
        allow_replace=allow_replace,
    )

    script.replace_material_by_name(
        config.slots.image,
        cc.VideoMaterial(str(image_path)),
    )
    script.replace_material_by_name(
        config.slots.audio,
        cc.AudioMaterial(str(audio_path)),
    )

    for text_slot in config.slots.texts:
        track = script.get_imported_track(
            cc.TrackType.text,
            name=text_slot.track_name,
            index=None if text_slot.track_name else text_slot.track_index,
        )
        script.replace_text(track, text_slot.segment_index, text_slot.content)

    _copy_media_into_draft(draft_name, config, image_path, audio_path)
    script.save()
    return draft_name, script


def _copy_media_into_draft(
    draft_name: str,
    config: TemplateConfig,
    image_path: Path,
    audio_path: Path,
) -> None:
    """Copy input media into the draft folder so CapCut can resolve them reliably."""
    draft_dir = config.drafts_dir / draft_name
    if not draft_dir.is_dir():
        return

    for source, target_name in (
        (image_path, Path(config.slots.image).name),
        (audio_path, Path(config.slots.audio).name),
    ):
        target = draft_dir / target_name
        if target.resolve() == source.resolve():
            continue
        shutil.copy2(source, target)
