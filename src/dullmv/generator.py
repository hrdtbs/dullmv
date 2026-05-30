"""Generate video from DSL effect description."""

from __future__ import annotations

import bisect
import math
from pathlib import Path

import librosa
import numpy as np
from moviepy import AudioFileClip, VideoClip
from PIL import Image, ImageFont

from dullmv.engine import (
    RENDERERS,
    _get_light_overlay_blobs,
    _get_smoke_blobs,
    _get_sparkle_blobs,
    render_blob_layers,
)
from dullmv.parser import parse_file


def _to_tuple(val, default=(1920, 1080)):
    if isinstance(val, (tuple, list)):
        return tuple(int(v) for v in val)
    if isinstance(val, str):
        parts = val.split()
        return tuple(int(v) for v in parts)
    return default


def _to_float(val, default=0.0):
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def find_project_root(start: Path) -> Path:
    """Walk up from start until pyproject.toml is found; fallback to cwd."""
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd().resolve()


def default_output_path(dsl_path: Path) -> Path:
    project_root = find_project_root(dsl_path.parent)
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return outputs_dir / f"{dsl_path.stem}.mp4"


def resolve_media_path(path: Path | str, base_dir: Path) -> Path:
    """Resolve a media path relative to base_dir unless already absolute."""
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = base_dir / resolved
    return resolved.resolve()


def generate(
    dsl_path: Path,
    out_path: Path | None = None,
    *,
    base_image: Path | str | None = None,
    audio: Path | str | None = None,
) -> Path:
    dsl_path = dsl_path.resolve()
    dsl = parse_file(str(dsl_path))

    # ---- Globals ----
    g = dsl.get("globals", {})
    base_dir = dsl_path.parent
    img_ref = base_image if base_image is not None else g.get("base_image", "Bloom.png")
    audio_ref = audio if audio is not None else g.get("audio", "Bloom.wav")
    img_path = resolve_media_path(img_ref, base_dir)
    audio_path = resolve_media_path(audio_ref, base_dir)
    size = _to_tuple(g.get("size"))
    fps = int(g.get("fps", 30))
    opening_duration = _to_float(g.get("opening_duration"), 3.0)
    blob_scale = int(g.get("blob_scale", 8))
    beat_decay = _to_float(g.get("beat_decay"), 0.35)
    preset = g.get("preset", "medium")
    if isinstance(preset, list):
        preset = preset[0]

    # ---- Load audio first to determine default duration ----
    print("Loading audio and analyzing beats...")
    audio_full = AudioFileClip(str(audio_path))
    duration = _to_float(g.get("duration"), audio_full.duration)
    audio = audio_full.subclipped(0, duration)
    y, sr = librosa.load(str(audio_path), sr=None, offset=0.0, duration=duration)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.asarray(tempo).flat[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    print(f"Tempo: {tempo:.1f} BPM, Beats: {len(beat_times)}, Duration: {duration:.2f}s")

    hop = 512
    stft = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))

    # Pre-calculate global max for spectrum normalization
    n_bars = 96
    all_means = []
    # Bass intensity curve (20Hz–150Hz)
    freqs_bin = librosa.fft_frequencies(sr=sr, n_fft=2048)
    bass_mask = (freqs_bin >= 20) & (freqs_bin <= 150)
    bass_curve = []
    raw_heights = []
    for fi in range(stft.shape[1]):
        freqs = stft[:, fi]
        bins = np.array_split(freqs, n_bars)
        means = [np.mean(b) for b in bins]
        all_means.extend(means)
        raw_heights.append(means)
        bass_curve.append(np.mean(freqs[bass_mask]))
    global_max_mean = max(all_means) if all_means else 1.0
    print(f"Global max spectrum mean: {global_max_mean:.2f}")

    # Pre-compute spectrum bar heights for all frames (lookup table)
    spectrum_norm = (
        np.array(raw_heights) / global_max_mean
        if global_max_mean > 0
        else np.zeros_like(np.array(raw_heights))
    )

    # Smooth bass curve and normalize
    kernel = np.ones(3) / 3.0
    bass_curve_smooth = np.convolve(np.array(bass_curve), kernel, mode="same")
    bass_max = float(np.max(bass_curve_smooth)) if len(bass_curve_smooth) else 1.0
    bass_curve = (
        (bass_curve_smooth / bass_max).tolist() if bass_max > 0 else [0.0] * len(bass_curve_smooth)
    )

    # Detect bass onsets (local maxima with minimum prominence)
    bass_onsets = []
    for i in range(1, len(bass_curve) - 1):
        if (
            bass_curve[i] > bass_curve[i - 1]
            and bass_curve[i] > bass_curve[i + 1]
            and bass_curve[i] > 0.25
        ):
            bass_onsets.append(i * hop / sr)
    print(f"Detected bass onsets: {len(bass_onsets)}")

    # Pre-compute bass_shake raw shift values for all frames
    bass_shake_params = None
    for eff in dsl.get("effects", []):
        if eff.get("_name") == "bass_shake":
            bass_shake_params = eff
            break
    n_frames = int(np.ceil(duration * fps)) + 1
    if bass_shake_params and bass_onsets:
        bs = bass_shake_params
        amount = bs.get("amount", 18)
        decay = bs.get("decay", 0.4)
        osc_freq = bs.get("oscillation_freq", 14.0)
        idle_amount = bs.get("idle_amount", 2.5)
        idle_freq = bs.get("idle_freq", 3.0)
        y_ratio = bs.get("y_ratio", 1.0)
        pre_sx = np.zeros(n_frames, dtype=np.float32)
        pre_sy = np.zeros(n_frames, dtype=np.float32)
        for fi in range(n_frames):
            t = fi / fps
            tx = 0.0
            ty = 0.0
            onset_start = bisect.bisect_left(bass_onsets, t - decay)
            onset_end = bisect.bisect_right(bass_onsets, t)
            for j in range(onset_start, onset_end):
                onset_t = bass_onsets[j]
                dt = t - onset_t
                idx = min(int(onset_t * sr / hop), len(bass_curve) - 1)
                strength = bass_curve[idx] if idx < len(bass_curve) else 0.0
                env = math.exp(-dt / (decay / 2.5)) * strength
                phase = dt * osc_freq * 2 * math.pi
                impulse = env * math.sin(phase)
                tx += impulse
                ty += impulse * y_ratio
            idx = min(int(t * sr / hop), len(bass_curve) - 1)
            idle_intensity = bass_curve[idx] if idx < len(bass_curve) else 0.0
            idle_shift = idle_amount * idle_intensity
            idle_phase = t * idle_freq * 2 * math.pi
            tx += idle_shift * math.sin(idle_phase)
            ty += idle_shift * math.cos(idle_phase) * y_ratio
            pre_sx[fi] = tx * amount
            pre_sy[fi] = ty * amount
    else:
        pre_sx = np.zeros(n_frames, dtype=np.float32)
        pre_sy = np.zeros(n_frames, dtype=np.float32)

    # ---- Base image ----
    img = Image.open(img_path).convert("RGB")
    w0, h0 = img.size
    if w0 / h0 > size[0] / size[1]:
        new_h = size[1]
        new_w = int(w0 * new_h / h0)
    else:
        new_w = size[0]
        new_h = int(h0 * new_w / w0)
    img_tmp = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - size[0]) // 2
    t_crop = (new_h - size[1]) // 2
    img_base = img_tmp.crop((left, t_crop, left + size[0], t_crop + size[1]))
    img_np = np.array(img_base)

    # ---- Font ----
    font_path = g.get("font", "C:\\Windows\\Fonts\\impact.ttf")
    if isinstance(font_path, list):
        font_path = font_path[0]
    font_size = int(g.get("font_size", 140))
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    # ---- Build context ----
    def bass_intensity(t):
        idx = min(int(t * sr / hop), len(bass_curve) - 1)
        return float(bass_curve[idx])

    ctx = {
        "width": size[0],
        "height": size[1],
        "beat_times": beat_times,
        "stft": stft,
        "sr": sr,
        "hop": hop,
        "global_max_mean": global_max_mean,
        "font": font,
        "img_np": img_np,
        "blob_scale": blob_scale,
        "beat_decay": beat_decay,
        "opening_duration": opening_duration,
        "bass_intensity": bass_intensity,
        "bass_curve": bass_curve,
        "bass_onsets": bass_onsets,
        "spectrum_norm": spectrum_norm,
        "pre_sx": pre_sx,
        "pre_sy": pre_sy,
        "fps": fps,
    }

    effects = dsl.get("effects", [])

    def make_frame(t):
        arr = ctx["img_np"].copy().astype(np.uint16)
        deferred_alpha = []
        deferred_sparkle = None
        deferred_sparkle_boost = 2.5
        w, h = ctx["width"], ctx["height"]
        scale = ctx.get("blob_scale", 8)

        def _flush_blobs():
            nonlocal arr, deferred_alpha, deferred_sparkle
            if deferred_alpha:
                layer_arr = render_blob_layers(w, h, deferred_alpha, scale)
                alpha = layer_arr[:, :, 3:4].astype(np.float32) / 255.0
                rgb = layer_arr[:, :, :3].astype(np.float32)
                arr_f = arr.astype(np.float32)
                arr_f[:] = arr_f * (1.0 - alpha) + rgb * alpha
                arr = arr_f.clip(0, 255).astype(np.uint16)
                deferred_alpha.clear()
            if deferred_sparkle is not None:
                layer_arr = render_blob_layers(w, h, deferred_sparkle, scale)
                layer_alpha = layer_arr[:, :, 3:4].astype(np.float32) / 255.0
                layer_rgb = layer_arr[:, :, :3].astype(np.float32)
                arr_f = arr.astype(np.float32)
                arr_f[:] = arr_f + layer_rgb * layer_alpha * deferred_sparkle_boost
                arr = np.clip(arr_f, 0, 255).astype(np.uint16)
                deferred_sparkle = None

        for effect in effects:
            name = effect["_name"]
            if name == "light_overlay":
                deferred_alpha.extend(_get_light_overlay_blobs(effect, t, ctx))
            elif name == "smoke":
                deferred_alpha.extend(_get_smoke_blobs(effect, t, ctx))
            elif name == "sparkle":
                blobs, boost = _get_sparkle_blobs(effect, t, ctx)
                if blobs:
                    deferred_sparkle = blobs
                    deferred_sparkle_boost = boost
            else:
                _flush_blobs()
                renderer = RENDERERS.get(name)
                if renderer:
                    arr = renderer(effect, arr, t, ctx)

        _flush_blobs()
        return np.clip(arr, 0, 255).astype(np.uint8)

    clip = VideoClip(make_frame, duration=duration).with_fps(fps).with_audio(audio)

    if out_path is None:
        out_path = default_output_path(dsl_path)
    else:
        out_path = out_path.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Rendering {duration:.1f}s clip from DSL...")
    clip.write_videofile(
        str(out_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset=preset,
        threads=4,
        logger=None,
    )
    print(f"Saved: {out_path}")
    print("All done!")
    return out_path
