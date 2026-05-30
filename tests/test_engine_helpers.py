"""Tests for dullmv.engine helpers."""

import math

from dullmv.engine import _eval_param, _resolve_tuple, create_eval_env


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
