"""Generate video from DSL effect description."""

from __future__ import annotations

import bisect
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
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
    precompute_sparkle_lookup,
    render_blob_layers,
)
from dullmv.parser import parse_file


@dataclass
class ProfileStats:
    """Timing breakdown for frame generation and encoding."""

    frame_seconds: float = 0.0
    encode_seconds: float = 0.0
    effect_seconds: dict[str, float] = field(default_factory=dict)
    n_frames: int = 0
    workers: int = 1

    def print_summary(self) -> None:
        total = self.frame_seconds + self.encode_seconds
        print("--- Profile ---")
        print(f"Frames: {self.n_frames} (workers={self.workers})")
        print(
            f"Frame generation: {self.frame_seconds:.2f}s ({self._pct(self.frame_seconds, total)})"
        )
        print(
            f"Encoding:         {self.encode_seconds:.2f}s "
            f"({self._pct(self.encode_seconds, total)})"
        )
        print(f"Total:            {total:.2f}s")
        if self.effect_seconds:
            print("Effect time (cumulative across frames):")
            for name, secs in sorted(self.effect_seconds.items(), key=lambda x: -x[1]):
                print(f"  {name}: {secs:.2f}s")

    @staticmethod
    def _pct(part: float, whole: float) -> str:
        if whole <= 0:
            return "0%"
        return f"{100.0 * part / whole:.1f}%"


_WORKER_CTX: dict | None = None
_WORKER_EFFECTS: list | None = None
_WORKER_PROFILE: bool = False


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


def _to_int(val, default: int) -> int:
    if isinstance(val, int):
        return val
    try:
        return int(val)
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


def _load_font(font_path: str, font_size: int):
    try:
        return ImageFont.truetype(font_path, font_size)
    except Exception:
        return ImageFont.load_default()


def _make_bass_intensity(bass_curve: list[float], sr: int, hop: int):
    def bass_intensity(t):
        idx = min(int(t * sr / hop), len(bass_curve) - 1)
        return float(bass_curve[idx])

    return bass_intensity


def _serialize_ctx(ctx: dict) -> dict:
    """Return a pickle-safe copy of the render context."""
    skip = {
        "font",
        "bass_intensity",
        "_sparkle_state",
        "_text_overlay_cache",
        "_frame_buffer",
        "_float_buffer",
    }
    serialized = {k: v for k, v in ctx.items() if k not in skip}
    serialized["font_path"] = ctx.get("font_path")
    serialized["font_size"] = ctx.get("font_size")
    return serialized


def _deserialize_ctx(serialized: dict) -> dict:
    ctx = dict(serialized)
    ctx["font"] = _load_font(ctx["font_path"], ctx["font_size"])
    ctx["bass_intensity"] = _make_bass_intensity(ctx["bass_curve"], ctx["sr"], ctx["hop"])
    return ctx


def _init_worker(serialized_ctx: dict, effects: list, profile: bool) -> None:
    global _WORKER_CTX, _WORKER_EFFECTS, _WORKER_PROFILE
    _WORKER_CTX = _deserialize_ctx(serialized_ctx)
    _WORKER_EFFECTS = effects
    _WORKER_PROFILE = profile


def _render_frame_worker(fi: int) -> tuple[int, np.ndarray, dict[str, float] | None]:
    assert _WORKER_CTX is not None and _WORKER_EFFECTS is not None
    timings = {} if _WORKER_PROFILE else None
    frame = render_frame(fi, _WORKER_EFFECTS, _WORKER_CTX, profile_timings=timings)
    return fi, frame, timings


def render_frame(
    fi: int,
    effects: list,
    ctx: dict,
    *,
    profile_timings: dict[str, float] | None = None,
    reuse_buffers: bool = False,
) -> np.ndarray:
    """Render a single frame by index."""
    fps = ctx["fps"]
    t = fi / fps
    ctx["_frame_index"] = fi
    w, h = ctx["width"], ctx["height"]
    scale = ctx.get("blob_scale", 8)

    if reuse_buffers and "_frame_buffer" in ctx:
        arr = ctx["_frame_buffer"]
        np.copyto(arr, ctx["img_np"])
    else:
        arr = np.array(ctx["img_np"], dtype=np.uint16, copy=True)

    if reuse_buffers:
        if "_float_buffer" not in ctx:
            ctx["_float_buffer"] = np.empty((h, w, 3), dtype=np.float32)
        arr_f = ctx["_float_buffer"]
    else:
        arr_f = None

    deferred_alpha: list = []
    deferred_sparkle = None
    deferred_sparkle_boost = 2.5

    def _flush_blobs():
        nonlocal arr, deferred_alpha, deferred_sparkle
        if deferred_alpha:
            layer_arr = render_blob_layers(w, h, deferred_alpha, scale)
            alpha = layer_arr[:, :, 3:4].astype(np.float32) / 255.0
            rgb = layer_arr[:, :, :3].astype(np.float32)
            if arr_f is None:
                blended = arr.astype(np.float32)
            else:
                blended = arr_f
                blended[:] = arr
            blended[:] = blended * (1.0 - alpha) + rgb * alpha
            np.clip(blended, 0, 255, out=blended)
            arr[:] = blended.astype(np.uint16)
            deferred_alpha.clear()
        if deferred_sparkle is not None:
            layer_arr = render_blob_layers(w, h, deferred_sparkle, scale)
            layer_alpha = layer_arr[:, :, 3:4].astype(np.float32) / 255.0
            layer_rgb = layer_arr[:, :, :3].astype(np.float32)
            if arr_f is None:
                blended = arr.astype(np.float32)
            else:
                blended = arr_f
                blended[:] = arr
            blended[:] = blended + layer_rgb * layer_alpha * deferred_sparkle_boost
            np.clip(blended, 0, 255, out=blended)
            arr[:] = blended.astype(np.uint16)
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
                if profile_timings is not None:
                    start = time.perf_counter()
                    arr = renderer(effect, arr, t, ctx)
                    profile_timings[name] = profile_timings.get(name, 0.0) + (
                        time.perf_counter() - start
                    )
                else:
                    arr = renderer(effect, arr, t, ctx)

    _flush_blobs()
    return np.clip(arr, 0, 255).astype(np.uint8)


def _render_frames_parallel(
    n_frames: int,
    effects: list,
    ctx: dict,
    workers: int,
    profile: bool,
) -> tuple[list[np.ndarray], ProfileStats]:
    serialized = _serialize_ctx(ctx)
    stats = ProfileStats(n_frames=n_frames, workers=workers)
    frames: list[np.ndarray | None] = [None] * n_frames

    t0 = time.perf_counter()
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_worker,
        initargs=(serialized, effects, profile),
    ) as pool:
        for fi, frame, timings in pool.map(_render_frame_worker, range(n_frames), chunksize=4):
            frames[fi] = frame
            if timings:
                for name, secs in timings.items():
                    stats.effect_seconds[name] = stats.effect_seconds.get(name, 0.0) + secs
    stats.frame_seconds = time.perf_counter() - t0
    if any(f is None for f in frames):
        missing = sum(1 for f in frames if f is None)
        raise RuntimeError(f"Parallel frame rendering incomplete: {missing} missing frame(s)")
    return frames, stats


def _render_frames_sequential(
    n_frames: int,
    effects: list,
    ctx: dict,
    profile: bool,
) -> tuple[list[np.ndarray], ProfileStats]:
    stats = ProfileStats(n_frames=n_frames, workers=1)
    h, w = ctx["height"], ctx["width"]
    ctx["_frame_buffer"] = np.empty((h, w, 3), dtype=np.uint16)
    ctx["_float_buffer"] = np.empty((h, w, 3), dtype=np.float32)

    frames: list[np.ndarray] = []
    t0 = time.perf_counter()
    for fi in range(n_frames):
        timings = {} if profile else None
        frame = render_frame(fi, effects, ctx, profile_timings=timings, reuse_buffers=True)
        frames.append(frame)
        if timings:
            for name, secs in timings.items():
                stats.effect_seconds[name] = stats.effect_seconds.get(name, 0.0) + secs
    stats.frame_seconds = time.perf_counter() - t0
    return frames, stats


def generate(
    dsl_path: Path,
    out_path: Path | None = None,
    *,
    base_image: Path | str | None = None,
    audio: Path | str | None = None,
    workers: int | None = None,
    profile: bool | None = None,
) -> Path:
    dsl_path = dsl_path.resolve()
    dsl = parse_file(str(dsl_path))

    if profile is None:
        profile = os.environ.get("DULLMV_PROFILE", "").lower() in ("1", "true", "yes")

    g = dsl.get("globals", {})
    base_dir = dsl_path.parent
    img_ref = base_image if base_image is not None else g.get("base_image", "Bloom.png")
    audio_ref = audio if audio is not None else g.get("audio", "Bloom.wav")
    img_path = resolve_media_path(img_ref, base_dir)
    audio_path = resolve_media_path(audio_ref, base_dir)
    size = _to_tuple(g.get("size"))
    design_size = _to_tuple(g.get("design_size"))
    fps = int(g.get("fps", 30))
    opening_duration = _to_float(g.get("opening_duration"), 3.0)
    blob_scale = int(g.get("blob_scale", 8))
    beat_decay = _to_float(g.get("beat_decay"), 0.35)
    preset = g.get("preset", "medium")
    if isinstance(preset, list):
        preset = preset[0]
    encode_threads = _to_int(g.get("threads"), os.cpu_count() or 4)

    if workers is None:
        workers = _to_int(g.get("workers"), os.cpu_count() or 1)
    workers = max(1, workers)

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

    n_bars = 96
    all_means = []
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

    spectrum_norm = (
        np.array(raw_heights) / global_max_mean
        if global_max_mean > 0
        else np.zeros_like(np.array(raw_heights))
    )

    kernel = np.ones(3) / 3.0
    bass_curve_smooth = np.convolve(np.array(bass_curve), kernel, mode="same")
    bass_max = float(np.max(bass_curve_smooth)) if len(bass_curve_smooth) else 1.0
    bass_curve_list = (
        (bass_curve_smooth / bass_max).tolist() if bass_max > 0 else [0.0] * len(bass_curve_smooth)
    )

    bass_onsets = []
    for i in range(1, len(bass_curve_list) - 1):
        if (
            bass_curve_list[i] > bass_curve_list[i - 1]
            and bass_curve_list[i] > bass_curve_list[i + 1]
            and bass_curve_list[i] > 0.25
        ):
            bass_onsets.append(i * hop / sr)
    print(f"Detected bass onsets: {len(bass_onsets)}")

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
                idx = min(int(onset_t * sr / hop), len(bass_curve_list) - 1)
                strength = bass_curve_list[idx] if idx < len(bass_curve_list) else 0.0
                env = math.exp(-dt / (decay / 2.5)) * strength
                phase = dt * osc_freq * 2 * math.pi
                impulse = env * math.sin(phase)
                tx += impulse
                ty += impulse * y_ratio
            idx = min(int(t * sr / hop), len(bass_curve_list) - 1)
            idle_intensity = bass_curve_list[idx] if idx < len(bass_curve_list) else 0.0
            idle_shift = idle_amount * idle_intensity
            idle_phase = t * idle_freq * 2 * math.pi
            tx += idle_shift * math.sin(idle_phase)
            ty += idle_shift * math.cos(idle_phase) * y_ratio
            pre_sx[fi] = tx * amount
            pre_sy[fi] = ty * amount
    else:
        pre_sx = np.zeros(n_frames, dtype=np.float32)
        pre_sy = np.zeros(n_frames, dtype=np.float32)

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

    font_path = g.get("font", "C:\\Windows\\Fonts\\impact.ttf")
    if isinstance(font_path, list):
        font_path = font_path[0]
    font_size = int(g.get("font_size", 140))
    font = _load_font(font_path, font_size)

    ctx = {
        "width": size[0],
        "height": size[1],
        "design_size": design_size,
        "beat_times": beat_times,
        "stft": stft,
        "sr": sr,
        "hop": hop,
        "global_max_mean": global_max_mean,
        "font": font,
        "font_path": font_path,
        "font_size": font_size,
        "img_np": img_np,
        "blob_scale": blob_scale,
        "beat_decay": beat_decay,
        "opening_duration": opening_duration,
        "bass_intensity": _make_bass_intensity(bass_curve_list, sr, hop),
        "bass_curve": bass_curve_list,
        "bass_onsets": bass_onsets,
        "spectrum_norm": spectrum_norm,
        "pre_sx": pre_sx,
        "pre_sy": pre_sy,
        "fps": fps,
        "_sparkle_lookup": {},
    }

    effects = dsl.get("effects", [])
    for idx, effect in enumerate(effects):
        if effect.get("_name") == "sparkle":
            sparkle_id = f"sparkle_{idx}"
            effect["_sparkle_id"] = sparkle_id
            print(f"Precomputing sparkle lookup ({n_frames} frames)...")
            ctx["_sparkle_lookup"][sparkle_id] = precompute_sparkle_lookup(
                effect, n_frames, fps, ctx
            )

    print(f"Rendering {duration:.1f}s clip ({n_frames} frames, workers={workers})...")
    if workers > 1:
        frames, profile_stats = _render_frames_parallel(n_frames, effects, ctx, workers, profile)
    else:
        frames, profile_stats = _render_frames_sequential(n_frames, effects, ctx, profile)

    def make_frame(t):
        fi = min(int(t * fps), len(frames) - 1)
        return frames[fi]

    clip = VideoClip(make_frame, duration=duration).with_fps(fps).with_audio(audio)

    if out_path is None:
        out_path = default_output_path(dsl_path)
    else:
        out_path = out_path.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

    encode_start = time.perf_counter()
    clip.write_videofile(
        str(out_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset=preset,
        threads=encode_threads,
        logger=None,
    )
    profile_stats.encode_seconds = time.perf_counter() - encode_start

    if profile:
        profile_stats.print_summary()

    print(f"Saved: {out_path}")
    print("All done!")
    return out_path
