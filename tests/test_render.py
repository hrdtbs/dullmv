"""Render pipeline and pixel regression tests."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image

from dullmv.engine import (
    _alpha_composite_overlay,
    _build_text_overlay_rgba,
    _get_light_overlay_blobs,
    _get_sparkle_blobs,
    precompute_blob_lookup,
    precompute_sparkle_lookup,
    precompute_text_overlay_lookup,
    render_bass_shake,
    render_blob_layers,
    render_glitch,
    render_spectrum,
)
from dullmv.generator import (
    _load_font,
    _precompute_effect_lookups,
    render_frame,
)
from dullmv.parser import parse_file

_TEMPLATE_DSL = Path(__file__).resolve().parents[1] / "dsl" / "template.dsl"


def load_template_effects() -> list[dict]:
    dsl = parse_file(str(_TEMPLATE_DSL))
    return dsl.get("effects", [])


def _base_ctx(w=320, h=180, fps=30, n_frames=90):
    img_np = np.zeros((h, w, 3), dtype=np.uint8)
    img_np[:, :, 1] = 80
    spectrum_norm = np.linspace(0.1, 1.0, 96, dtype=np.float32)
    spectrum_norm = np.tile(spectrum_norm, (10, 1))
    bass_curve = [0.5] * 100
    font_path = "C:\\Windows\\Fonts\\impact.ttf"
    font_size = 24
    return {
        "width": w,
        "height": h,
        "design_size": (1920, 1080),
        "fps": fps,
        "sr": 44100,
        "hop": 512,
        "stft": np.ones((1025, 100), dtype=np.float32),
        "global_max_mean": 1.0,
        "img_np": img_np,
        "blob_scale": 8,
        "opening_duration": 3.0,
        "bass_curve": bass_curve,
        "bass_intensity": lambda t: 0.5,
        "beat_times": np.array([0.0, 0.5, 1.0]),
        "spectrum_norm": spectrum_norm,
        "pre_sx": np.zeros(n_frames, dtype=np.float32),
        "pre_sy": np.zeros(n_frames, dtype=np.float32),
        "_sparkle_lookup": {},
        "_blob_lookup": {},
        "_text_overlay_lookup": {},
        "font_path": font_path,
        "font_size": font_size,
        "font": _load_font(font_path, font_size),
    }


def _prepare_effects(effects: list, ctx: dict, n_frames: int = 90) -> list:
    prepared = deepcopy(effects)
    _precompute_effect_lookups(prepared, n_frames, ctx["fps"], ctx, ctx["opening_duration"])
    return prepared


def _parallel_frames(effects: list, ctx: dict, n_frames: int) -> list[np.ndarray]:
    from dullmv import generator as gen_mod

    serialized = gen_mod._serialize_ctx(ctx)
    gen_mod._init_worker(serialized, effects, False)
    return [gen_mod._render_frame_worker(fi)[1] for fi in range(n_frames)]


def _sequential_frames(effects: list, ctx: dict, n_frames: int) -> list[np.ndarray]:
    return [render_frame(fi, effects, dict(ctx)) for fi in range(n_frames)]


def test_render_blob_layers_shape_and_alpha():
    blobs = [
        {
            "cx": 160,
            "cy": 90,
            "rx": 40,
            "ry": 30,
            "color": (255, 200, 100),
            "alpha": 180,
        }
    ]
    layer = render_blob_layers(320, 180, blobs, scale=8)
    assert layer.shape == (180, 320, 4)
    assert layer[:, :, 3].max() > 0


def test_render_spectrum_vectorized():
    ctx = _base_ctx()
    frame = np.full((180, 320, 3), 40, dtype=np.uint16)
    params = {"bars": 96, "max_height_ratio": 0.35, "color": (255, 255, 255), "alpha": 150}
    out = render_spectrum(params, frame, t=0.1, ctx=ctx)
    assert out.shape == frame.shape
    assert out[:, -10:, :].max() > frame[:, -10:, :].max()


def test_render_bass_shake_rgb_split():
    ctx = _base_ctx()
    ctx["pre_sx"][:] = 3.0
    ctx["pre_sy"][:] = 2.0
    frame = np.random.default_rng(0).integers(0, 256, (180, 320, 3), dtype=np.uint16)
    params = {"rgb_split": 3, "direction": "both", "oscillation_freq": 7.0}
    out = render_bass_shake(params, frame, t=0.5, ctx=ctx)
    assert out.shape == frame.shape
    assert not np.array_equal(out, frame)


def test_render_glitch_deterministic():
    ctx = _base_ctx()
    frame = np.random.default_rng(1).integers(0, 256, (180, 320, 3), dtype=np.uint16)
    params = {"probability": 1.0, "corner_ratio": 0.22, "max_waves": 2, "min_shift": 1}
    out1 = render_glitch(params, frame.copy(), t=1.0, ctx=ctx)
    out2 = render_glitch(params, frame.copy(), t=1.0, ctx=ctx)
    assert np.array_equal(out1, out2)


def test_sparkle_lookup_matches_sequential():
    ctx = _base_ctx()
    params = {
        "_sparkle_id": "sparkle_0",
        "spots": 4,
        "base_radius": 20,
        "radius_var": 10,
        "base_alpha": 200,
        "color": (255, 255, 255),
        "edge_bias": 0.8,
        "intensity_scale": 2.0,
        "pulse_freq": 10.0,
        "decay": 0.35,
        "central_exclusion": 0.4,
        "brightness_boost": 3.5,
        "fade_mode": "exponential",
        "alpha_cutoff": 0.0,
    }
    n_frames = 60
    lookup = precompute_sparkle_lookup(params, n_frames, ctx["fps"], ctx)
    ctx["_sparkle_lookup"] = {"sparkle_0": lookup}

    for fi in range(n_frames):
        t = fi / ctx["fps"]
        ctx["_frame_index"] = fi
        ctx.pop("_sparkle_state", None)
        sequential = _get_sparkle_blobs(params, t, ctx)
        from_lookup = lookup[fi]
        assert sequential[0] == from_lookup[0]
        assert sequential[1] == from_lookup[1]


def test_render_frame_representative_pixels():
    ctx = _base_ctx()
    effects = [
        {
            "_name": "spectrum",
            "bars": 96,
            "max_height_ratio": 0.35,
            "color": (255, 255, 255),
            "alpha": 150,
        },
        {
            "_name": "glitch",
            "probability": 1.0,
            "corner_ratio": 0.22,
            "max_waves": 1,
            "min_shift": 2,
        },
    ]
    frame15 = render_frame(15, effects, ctx)
    frame30 = render_frame(30, effects, dict(_base_ctx()))
    assert frame15.shape == (180, 320, 3)
    assert frame15.dtype == np.uint8
    assert frame15[179, 160, 0] == 150
    assert frame15[179, 160, 1] == 182
    assert frame15[179, 160, 2] == 150
    assert int(frame15.sum()) == 9657924
    assert int(frame30.sum()) == 9657924


def test_parallel_matches_sequential(monkeypatch):
    ctx = _base_ctx(n_frames=10)
    effects = [
        {
            "_name": "spectrum",
            "bars": 96,
            "color": (255, 255, 255),
            "alpha": 150,
        },
    ]
    n_frames = 10
    seq_frames = _sequential_frames(effects, ctx, n_frames)
    par_frames = _parallel_frames(effects, ctx, n_frames)

    for fi in range(n_frames):
        assert np.array_equal(seq_frames[fi], par_frames[fi]), f"frame {fi} mismatch"


def test_blob_lookup_matches_sequential():
    ctx = _base_ctx(n_frames=30)
    params = {
        "_name": "light_overlay",
        "blob": {
            "anchor": (0.5, 0.5),
            "color": (255, 200, 100),
            "cx": "int(width * 0.5 + 20 * sin(t))",
            "cy": "int(height * 0.5 + 10 * cos(t))",
            "rx": 40,
            "ry": 30,
            "alpha": 120,
        },
    }
    n_frames = 30
    lookup = precompute_blob_lookup(params, n_frames, ctx["fps"], ctx, compute_dist_ratio=False)
    params["_blob_id"] = "light_overlay_0"
    ctx["_blob_lookup"] = {"light_overlay_0": lookup}

    for fi in range(n_frames):
        t = fi / ctx["fps"]
        ctx["_frame_index"] = fi
        sequential = _get_light_overlay_blobs(params, t, ctx, _use_cache=False)
        from_lookup = _get_light_overlay_blobs(params, t, ctx)
        assert sequential == from_lookup


def test_text_overlay_precompute_matches():
    ctx = _base_ctx(n_frames=30)
    params = {
        "_name": "text",
        "color": (255, 255, 255),
        "line": {
            "text": "TEST",
            "start_time": 0.0,
            "slide_duration": 0.9,
            "fade_duration": 0.6,
            "start_pos": (-0.4, 0.5),
            "end_pos": (0.1, 0.5),
            "easing": "ease_out_cubic",
        },
    }
    n_frames = 30
    lookup = precompute_text_overlay_lookup(
        params, n_frames, ctx["fps"], ctx, ctx["opening_duration"]
    )
    for fi in range(min(n_frames, len(lookup))):
        t = fi / ctx["fps"]
        expected = _build_text_overlay_rgba(params, t, ctx)
        assert np.array_equal(lookup[fi], expected)


def test_text_compose_matches_pil():
    ctx = _base_ctx(n_frames=10)
    params = {
        "color": (255, 255, 255),
        "line": {
            "text": "X",
            "start_time": 0.0,
            "slide_duration": 0.5,
            "fade_duration": 0.5,
            "start_pos": (0.2, 0.5),
            "end_pos": (0.2, 0.5),
        },
    }
    frame = np.random.default_rng(2).integers(0, 256, (180, 320, 3), dtype=np.uint16)
    overlay = _build_text_overlay_rgba(params, 0.1, ctx)
    via_helper = _alpha_composite_overlay(frame, overlay)
    base_img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).convert("RGBA")
    via_pil = np.array(
        Image.alpha_composite(base_img, Image.fromarray(overlay)).convert("RGB")
    ).astype(np.uint16)
    assert np.array_equal(via_helper, via_pil)


def test_template_effects_parallel_matches_sequential():
    ctx = _base_ctx(n_frames=90)
    ctx["pre_sx"][15:25] = 3.0
    ctx["pre_sy"][15:25] = 2.0
    effects = _prepare_effects(load_template_effects(), ctx, n_frames=90)
    n_frames = 90
    seq_frames = _sequential_frames(effects, ctx, n_frames)
    par_frames = _parallel_frames(effects, ctx, n_frames)

    for fi in range(n_frames):
        assert np.array_equal(seq_frames[fi], par_frames[fi]), f"frame {fi} mismatch"
