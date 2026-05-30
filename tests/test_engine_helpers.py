"""Tests for dullmv.engine helpers."""

import math

from dullmv.engine import (
    _eval_param,
    _get_light_overlay_blobs,
    _get_smoke_blobs,
    _resolve_tuple,
    _scale_blob_coords,
    create_eval_env,
)


def test_resolve_tuple_relative():
    x, y = _resolve_tuple((0.5, 0.25), 1280, 720)
    assert x == 640
    assert y == 180


def test_resolve_tuple_absolute():
    x, y = _resolve_tuple((100, 200), 1280, 720)
    assert x == 100
    assert y == 200


def test_resolve_tuple_negative_relative():
    x, y = _resolve_tuple((-0.5, 0.5), 1280, 720)
    assert x == -640
    assert y == 360


def test_eval_param_expression():
    env = create_eval_env(t=1.0, width=1280, height=720, index=2)
    assert _eval_param("sin(t) + index", env) == math.sin(1.0) + 2


def test_eval_param_literal_passthrough():
    env = create_eval_env(t=0.0, width=100, height=100)
    assert _eval_param(42, env) == 42
    assert _eval_param((255, 255, 255), env) == (255, 255, 255)


def test_scale_blob_coords_from_design_to_720p():
    cx, cy, rx, ry = _scale_blob_coords(960, 540, 140, 100, 1280, 720, 1920, 1080)
    assert cx == 640
    assert cy == 360
    assert rx == int(140 * 1280 / 1920)
    assert ry == int(100 * 720 / 1080)


def test_scale_blob_coords_identity_at_design_size():
    cx, cy, rx, ry = _scale_blob_coords(960, 540, 140, 100, 1920, 1080, 1920, 1080)
    assert (cx, cy, rx, ry) == (960, 540, 140, 100)


def test_blob_effects_scale_from_design_size():
    params = {
        "blob": {
            "anchor": (0.5, 0.5),
            "color": (255, 255, 255),
            "cx": "anchor_x + 100",
            "cy": "anchor_y + 50",
            "rx": 180,
            "ry": 120,
            "alpha": 110,
        }
    }
    ctx_1080 = {"width": 1920, "height": 1080, "design_size": (1920, 1080)}
    ctx_720 = {"width": 1280, "height": 720, "design_size": (1920, 1080)}

    smoke_1080 = _get_smoke_blobs(params, 0.0, ctx_1080)[0]
    smoke_720 = _get_smoke_blobs(params, 0.0, ctx_720)[0]
    light_1080 = _get_light_overlay_blobs(params, 0.0, ctx_1080)[0]
    light_720 = _get_light_overlay_blobs(params, 0.0, ctx_720)[0]

    for b1080, b720 in ((smoke_1080, smoke_720), (light_1080, light_720)):
        assert b720["cx"] == int(b1080["cx"] * 1280 / 1920)
        assert b720["cy"] == int(b1080["cy"] * 720 / 1080)
        assert b720["rx"] == int(b1080["rx"] * 1280 / 1920)
        assert b720["ry"] == int(b1080["ry"] * 720 / 1080)
        assert b720["alpha"] == b1080["alpha"]
