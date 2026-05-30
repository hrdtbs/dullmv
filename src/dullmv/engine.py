"""Effect rendering engine with expression evaluation."""

import bisect
import math
import random as py_random

import cv2
import numpy as np
from PIL import Image, ImageDraw

SAFE_BUILTINS = {}


def create_eval_env(t, width, height, ctx=None, index=None, **extra):
    """Create a safe evaluation environment for expression strings."""
    env = {
        "t": t,
        "width": width,
        "height": height,
        "pi": math.pi,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "pow": pow,
        "abs": abs,
        "min": min,
        "max": max,
        "int": int,
        "float": float,
        "round": round,
        "random": py_random.random,
        "seed": py_random.seed,
        "radians": math.radians,
        "degrees": math.degrees,
        "exp": math.exp,
        "log": math.log,
        "ceil": math.ceil,
        "floor": math.floor,
    }
    if index is not None:
        env["index"] = index
    if ctx and "beat_times" in ctx:
        env["beat_intensity"] = lambda decay=0.35: _beat_intensity(t, ctx["beat_times"], decay)
    env.update(extra)
    return env


def _eval_param(value, env):
    """Evaluate a parameter value. Strings are treated as expressions."""
    if isinstance(value, str):
        return eval(value, {"__builtins__": SAFE_BUILTINS}, env)
    return value


def _beat_intensity(t, beat_times, decay):

    idx = bisect.bisect_left(beat_times, t)
    best = 0.0
    for i in (idx, idx - 1):
        if 0 <= i < len(beat_times):
            diff = t - beat_times[i]
            if 0 <= diff < decay:
                best = max(best, 1.0 - (diff / decay))
    return best


def _resolve_tuple(value, w, h):
    """Interpret a 2-element tuple as either relative (-1.0~1.0 float) or absolute pixels."""
    if not isinstance(value, (tuple, list)) or len(value) < 2:
        return value
    x, y = value[0], value[1]
    if isinstance(x, float) and -1.0 <= x <= 1.0:
        rx = int(x * w + (0.5 if x >= 0 else -0.5))
    else:
        rx = x
    if isinstance(y, float) and -1.0 <= y <= 1.0:
        ry = int(y * h + (0.5 if y >= 0 else -0.5))
    else:
        ry = y
    return (int(rx), int(ry))


def render_blob_layers(w, h, blobs, scale=8):
    sw, sh = w // scale, h // scale
    pad = 50
    psw, psh = sw + 2 * pad, sh + 2 * pad
    ys, xs = np.ogrid[:psh, :psw]
    acc_rgb = np.zeros((psh, psw, 3), dtype=np.float32)
    acc_alpha = np.zeros((psh, psw), dtype=np.float32)
    for b in blobs:
        cx_s = b["cx"] / scale + pad
        cy_s = b["cy"] / scale + pad
        sx = max(b["rx"] / scale * 1.2, 1.0)
        sy = max(b["ry"] / scale * 1.2, 1.0)
        d2 = ((xs - cx_s) / sx) ** 2 + ((ys - cy_s) / sy) ** 2
        base = np.exp(-d2)
        halo = 0.25 * np.exp(-d2 * 0.3)
        alpha = b["alpha"] * (base + halo)
        cr, cg, cb = b["color"]
        acc_rgb[:, :, 0] += cr * alpha
        acc_rgb[:, :, 1] += cg * alpha
        acc_rgb[:, :, 2] += cb * alpha
        acc_alpha += alpha
    mask = acc_alpha > 0
    safe_alpha = np.where(mask, acc_alpha, 1.0)
    canvas = np.zeros((psh, psw, 4), dtype=np.float32)
    for c in range(3):
        canvas[:, :, c] = np.where(mask, acc_rgb[:, :, c] / safe_alpha, 0)
    canvas[:, :, 3] = np.clip(acc_alpha, 0, 255)
    canvas = np.clip(canvas, 0, 255).astype(np.uint8)
    cropped = canvas[pad : pad + sh, pad : pad + sw]
    upscaled = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
    return upscaled.astype(np.uint16)


def get_corners(h, w, ratio=0.25):
    cw = int(w * ratio)
    ch = int(h * ratio)
    return [
        (0, 0, cw, ch),
        (w - cw, 0, w, ch),
        (0, h - ch, cw, h),
        (w - cw, h - ch, w, h),
    ]


def shift_region_horizontal(region, shift):
    h, w = region.shape[:2]
    if shift == 0:
        return region.copy()
    result = np.zeros_like(region)
    if shift > 0:
        result[:, shift:] = region[:, :-shift]
    else:
        result[:, : w + shift] = region[:, -shift:]
    return result


def ease_out_cubic(x):
    return 1 - pow(1 - x, 3)


EASINGS = {
    "ease_out_cubic": ease_out_cubic,
    "linear": lambda x: x,
}


# ---------------------------------------------------------------------------
# Effect renderers
# ---------------------------------------------------------------------------


def _get_light_overlay_blobs(params, t, ctx):
    w, h = ctx["width"], ctx["height"]
    blobs_def = params.get("blob", [])
    if not isinstance(blobs_def, list):
        blobs_def = [blobs_def]
    blobs = []
    for i, bdef in enumerate(blobs_def):
        env = create_eval_env(t, w, h, ctx, index=i)
        anchor = bdef.get("anchor", (0, 0))
        if isinstance(anchor, list):
            anchor = tuple(anchor)
        anchor = _resolve_tuple(anchor, w, h)
        color = bdef.get("color", (255, 255, 255))
        if isinstance(color, list):
            color = tuple(color)
        env["anchor_x"] = anchor[0] if len(anchor) > 0 else 0
        env["anchor_y"] = anchor[1] if len(anchor) > 1 else 0
        cx = _eval_param(bdef.get("cx", anchor[0]), env)
        cy = _eval_param(bdef.get("cy", anchor[1]), env)
        rx = _eval_param(bdef.get("rx", 100), env)
        ry = _eval_param(bdef.get("ry", 100), env)
        alpha = _eval_param(bdef.get("alpha", 255), env)
        blobs.append(
            {
                "cx": int(cx),
                "cy": int(cy),
                "rx": int(rx),
                "ry": int(ry),
                "color": color,
                "alpha": int(alpha),
            }
        )
    return blobs


def render_light_overlay(params, frame, t, ctx):
    blobs = _get_light_overlay_blobs(params, t, ctx)
    if blobs:
        w, h = ctx["width"], ctx["height"]
        scale = ctx.get("blob_scale", 8)
        layer_arr = render_blob_layers(w, h, blobs, scale)
        alpha = layer_arr[:, :, 3:4] / 255.0
        rgb = layer_arr[:, :, :3]
        frame = (frame * (1 - alpha) + rgb * alpha).astype(np.uint16)
    return frame


def render_spectrum(params, frame, t, ctx):
    h, w = frame.shape[:2]
    n_bars = params.get("bars", 96)
    max_h_ratio = params.get("max_height_ratio", 0.35)
    color = params.get("color", (255, 255, 255))
    if isinstance(color, list):
        color = tuple(color)
    alpha = params.get("alpha", 150)
    boost = params.get("boost", 1.2)

    max_h = int(h * max_h_ratio)
    bar_w = w / n_bars

    sr = ctx["sr"]
    hop = ctx["hop"]
    spectrum_norm = ctx.get("spectrum_norm")

    frame_idx = min(int(t * sr / hop), spectrum_norm.shape[0] - 1)
    norms = spectrum_norm[frame_idx]
    heights = np.minimum((norms * max_h * boost).astype(np.int32), max_h)

    cr, cg, cb = color
    base_alpha = alpha / 255.0
    inv_alpha = 1.0 - base_alpha
    result = frame.astype(np.float32)

    cols = np.arange(w, dtype=np.int32)
    bar_idx = np.minimum((cols / bar_w).astype(np.int32), n_bars - 1)
    bar_heights = heights[bar_idx]
    rows = np.arange(h, dtype=np.int32)
    mask = rows[:, None] >= (h - bar_heights)[None, :]

    result[:, :, 0] = np.where(mask, result[:, :, 0] * inv_alpha + cr * base_alpha, result[:, :, 0])
    result[:, :, 1] = np.where(mask, result[:, :, 1] * inv_alpha + cg * base_alpha, result[:, :, 1])
    result[:, :, 2] = np.where(mask, result[:, :, 2] * inv_alpha + cb * base_alpha, result[:, :, 2])
    return np.clip(result, 0, 255).astype(np.uint16)


def _get_smoke_blobs(params, t, ctx):
    w, h = ctx["width"], ctx["height"]
    blobs_def = params.get("blob", [])
    if not isinstance(blobs_def, list):
        blobs_def = [blobs_def]
    max_dist = math.sqrt((w / 2) ** 2 + (h / 2) ** 2)
    blobs = []
    for i, bdef in enumerate(blobs_def):
        env = create_eval_env(t, w, h, ctx, index=i)
        anchor = bdef.get("anchor", (0, 0))
        if isinstance(anchor, list):
            anchor = tuple(anchor)
        anchor = _resolve_tuple(anchor, w, h)
        color = bdef.get("color", (255, 255, 255))
        if isinstance(color, list):
            color = tuple(color)
        env["anchor_x"] = anchor[0] if len(anchor) > 0 else 0
        env["anchor_y"] = anchor[1] if len(anchor) > 1 else 0
        cx = _eval_param(bdef.get("cx", anchor[0]), env)
        cy = _eval_param(bdef.get("cy", anchor[1]), env)
        dx = cx - w / 2
        dy = cy - h / 2
        dist = math.sqrt(dx * dx + dy * dy)
        dist_ratio = min(dist / max_dist, 1.0) if max_dist > 0 else 0
        env["dist_ratio"] = dist_ratio
        rx = _eval_param(bdef.get("rx", 100), env)
        ry = _eval_param(bdef.get("ry", 100), env)
        alpha = _eval_param(bdef.get("alpha", 100), env)
        blobs.append(
            {
                "cx": int(cx),
                "cy": int(cy),
                "rx": int(rx),
                "ry": int(ry),
                "color": color,
                "alpha": int(alpha),
            }
        )
    return blobs


def render_smoke(params, frame, t, ctx):
    blobs = _get_smoke_blobs(params, t, ctx)
    if blobs:
        w, h = ctx["width"], ctx["height"]
        scale = ctx.get("blob_scale", 8)
        layer_arr = render_blob_layers(w, h, blobs, scale)
        alpha = layer_arr[:, :, 3:4] / 255.0
        rgb = layer_arr[:, :, :3]
        frame = (frame * (1 - alpha) + rgb * alpha).astype(np.uint16)
    return frame


def _build_text_overlay_rgba(params, t, ctx):
    w, h = ctx["width"], ctx["height"]
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = ctx.get("font")
    color = params.get("color", (255, 255, 255))
    if isinstance(color, list):
        color = tuple(color)

    fade_out_start = params.get("fade_out_start", 2.0)
    fade_out_duration = params.get("fade_out_duration", 1.0)

    if t < fade_out_start:
        fade_out = 1.0
    else:
        fade_out = max(0.0, 1.0 - (t - fade_out_start) / fade_out_duration)

    lines_def = params.get("line", [])
    if not isinstance(lines_def, list):
        lines_def = [lines_def]

    for ldef in lines_def:
        text_str = ldef.get("text", "")
        start_time = ldef.get("start_time", 0.0)
        slide_dur = ldef.get("slide_duration", 0.9)
        fade_dur = ldef.get("fade_duration", 0.6)

        start_pos = ldef.get("start_pos", (0, 0))
        if isinstance(start_pos, list):
            start_pos = tuple(start_pos)
        start_pos = _resolve_tuple(start_pos, w, h)
        end_pos = ldef.get("end_pos", (0, 0))
        if isinstance(end_pos, list):
            end_pos = tuple(end_pos)
        end_pos = _resolve_tuple(end_pos, w, h)

        easing_name = ldef.get("easing", "ease_out_cubic")
        easing_fn = EASINGS.get(easing_name, lambda x: x)

        prog = min(max((t - start_time) / slide_dur, 0.0), 1.0)
        fade_prog = min(max((t - start_time) / fade_dur, 0.0), 1.0)

        x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * easing_fn(prog))
        y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * easing_fn(prog))
        alpha = int(255 * easing_fn(fade_prog) * fade_out)

        cr, cg, cb = color
        draw.text((x, y), text_str, font=font, fill=(cr, cg, cb, alpha))

    return np.array(overlay)


def render_text(params, frame, t, ctx):
    opening_dur = ctx.get("opening_duration", 3.0)
    if t >= opening_dur:
        return frame

    fps = ctx.get("fps", 30)
    fi = ctx.get("_frame_index", int(round(t * fps)))
    cache_key = (id(params), fi)
    cache = ctx.setdefault("_text_overlay_cache", {})
    if cache_key not in cache:
        cache[cache_key] = _build_text_overlay_rgba(params, t, ctx)

    overlay = cache[cache_key]
    base_img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).convert("RGBA")
    result = Image.alpha_composite(base_img, Image.fromarray(overlay))
    return np.array(result.convert("RGB")).astype(np.uint16)


def _apply_wave_shifts(region, shifts, min_shift):
    """Apply per-row horizontal shifts to a corner region block."""
    out = region.copy()
    for i, shift in enumerate(shifts):
        if abs(shift) < min_shift:
            continue
        row = region[i]
        if shift > 0:
            out[i, shift:] = row[:-shift]
        elif shift < 0:
            out[i, :shift] = row[-shift:]
    return out


def render_glitch(params, frame, t, ctx):
    h, w = frame.shape[:2]
    prob = params.get("probability", 0.10)
    corner_ratio = params.get("corner_ratio", 0.22)
    max_waves = params.get("max_waves", 2)
    min_shift = params.get("min_shift", 2)

    np.random.seed(int(t * 1000) % 2**16)
    result = frame.copy()
    corners = get_corners(h, w, corner_ratio)

    if np.random.random() < prob:
        for x1, y1, x2, y2 in corners:
            ch = y2 - y1
            n_waves = 1 + int(np.random.random() * max_waves)
            for _ in range(n_waves):
                env = create_eval_env(t, w, h, ctx)
                env["random"] = np.random.random
                wave_h_expr = params.get("wave_height", "8 + random() * 12")
                wave_h = int(_eval_param(wave_h_expr, env))

                wave_y = y1 + int(np.random.random() * max(1, ch - wave_h))
                y_end = min(wave_y + wave_h, y2)
                if wave_y >= y_end:
                    continue

                base_shift_expr = params.get("base_shift", "(random() - 0.5) * 10")
                base_shift = int(_eval_param(base_shift_expr, env))

                wave_rows = np.arange(wave_y, y_end)
                progress = (wave_rows - wave_y) / wave_h
                shifts = (base_shift * np.sin(progress * math.pi)).astype(np.int32)
                region = result[wave_y:y_end, x1:x2]
                result[wave_y:y_end, x1:x2] = _apply_wave_shifts(region, shifts, min_shift)
    return result


def _shift_with_edge_pad(arr, sx, sy):
    """Shift array using edge padding (no wrap-around artifacts)."""
    h, w = arr.shape[:2]
    pad_x = abs(int(sx))
    pad_y = abs(int(sy))
    padded = np.pad(arr, ((pad_y, pad_y), (pad_x, pad_x), (0, 0)), mode="edge")
    y0 = pad_y + int(sy)
    x0 = pad_x + int(sx)
    return padded[y0 : y0 + h, x0 : x0 + w]


def _shift_rgb_channels(frame, channel_shifts):
    """Shift RGB channels with a single pad operation."""
    h, w = frame.shape[:2]
    max_pad_x = max(abs(int(sx)) for sx, _ in channel_shifts)
    max_pad_y = max(abs(int(sy)) for _, sy in channel_shifts)
    padded = np.pad(frame, ((max_pad_y, max_pad_y), (max_pad_x, max_pad_x), (0, 0)), mode="edge")
    result = np.zeros_like(frame)
    for c, (sx, sy) in enumerate(channel_shifts):
        y0 = max_pad_y + int(sy)
        x0 = max_pad_x + int(sx)
        result[:, :, c] = padded[y0 : y0 + h, x0 : x0 + w, c]
    return result


def render_bass_shake(params, frame, t, ctx):
    fps = ctx.get("fps", 30)
    pre_sx = ctx.get("pre_sx")
    pre_sy = ctx.get("pre_sy")

    rgb_split = params.get("rgb_split", 5)
    direction = params.get("direction", "both")
    osc_freq = params.get("oscillation_freq", 14.0)

    if pre_sx is not None and pre_sy is not None:
        fi = min(int(round(t * fps)), len(pre_sx) - 1)
        total_shift_x = float(pre_sx[fi])
        total_shift_y = float(pre_sy[fi])
    else:
        return frame

    if direction == "horizontal":
        total_shift_y = 0.0
    elif direction == "vertical":
        total_shift_x = 0.0

    sx = int(total_shift_x)
    sy = int(total_shift_y)

    if rgb_split > 0 and (sx != 0 or sy != 0):
        phase = t * osc_freq
        offsets = [
            (math.sin(phase), math.cos(phase)),
            (math.sin(phase + 2.1), math.cos(phase + 2.1)),
            (math.sin(phase + 4.2), math.cos(phase + 4.2)),
        ]
        channel_shifts = []
        for ox_raw, oy_raw in offsets:
            ox = sx + int(rgb_split * ox_raw) if direction in ("horizontal", "both") else 0
            oy = sy + int(rgb_split * oy_raw) if direction in ("vertical", "both") else 0
            channel_shifts.append((ox, oy))
        return _shift_rgb_channels(frame, channel_shifts)

    if sx != 0 or sy != 0:
        ox = sx if direction in ("horizontal", "both") else 0
        oy = sy if direction in ("vertical", "both") else 0
        return _shift_with_edge_pad(frame, ox, oy)
    return frame


def _pick_sparkle_pos(w, h, edge_bias, central_exclusion):
    """Pick a sparkle position respecting edge_bias and central_exclusion."""
    margin = min(w, h) // 8
    max_attempts = 50
    for _ in range(max_attempts):
        if np.random.random() < edge_bias:
            edge = np.random.randint(0, 4)
            if edge == 0:
                x = np.random.randint(0, margin)
                y = np.random.randint(0, h)
            elif edge == 1:
                x = np.random.randint(w - margin, w)
                y = np.random.randint(0, h)
            elif edge == 2:
                x = np.random.randint(0, w)
                y = np.random.randint(0, margin)
            else:
                x = np.random.randint(0, w)
                y = np.random.randint(h - margin, h)
        else:
            x = np.random.randint(0, w)
            y = np.random.randint(0, h)

        if central_exclusion > 0:
            dx = abs(x - w / 2) / (w / 2)
            dy = abs(y - h / 2) / (h / 2)
            if dx < central_exclusion and dy < central_exclusion:
                continue
        return x, y
    edge = np.random.randint(0, 4)
    if edge == 0:
        return np.random.randint(0, margin), np.random.randint(0, h)
    if edge == 1:
        return np.random.randint(w - margin, w), np.random.randint(0, h)
    if edge == 2:
        return np.random.randint(0, w), np.random.randint(0, margin)
    return np.random.randint(0, w), np.random.randint(h - margin, h)


def _sparkle_intensity(params, t, ctx):
    intensity_scale = params.get("intensity_scale", 1.5)
    bass_fn = ctx.get("bass_intensity")
    if bass_fn:
        intensity = bass_fn(t)
    else:
        sr = ctx.get("sr", 44100)
        hop = ctx.get("hop", 512)
        stft = ctx.get("stft")
        global_max_mean = ctx.get("global_max_mean", 1.0)
        if stft is not None and global_max_mean > 0:
            frame_idx = min(int(t * sr / hop), stft.shape[1] - 1)
            freqs = stft[:, frame_idx]
            intensity = float(np.mean(freqs)) / global_max_mean
        else:
            intensity = 0.0
    return intensity * intensity_scale


def _sparkle_blobs_from_state(params, t, state):
    decay = params.get("decay", 0.15)
    fade_mode = params.get("fade_mode", "exponential")
    alpha_cutoff = params.get("alpha_cutoff", 0.0)
    brightness_boost = params.get("brightness_boost", 2.5)

    blobs = []
    for s in state:
        age = t - s["birth_t"]
        if age < 0:
            continue
        life_ratio = age / decay if decay > 0 else 1.0
        if fade_mode == "linear":
            fade = max(0.0, 1.0 - life_ratio)
        else:
            fade = math.exp(-3.0 * life_ratio)
        alpha = s["max_alpha"] * fade
        if alpha <= alpha_cutoff:
            continue
        blobs.append(
            {
                "cx": s["cx"],
                "cy": s["cy"],
                "rx": s["rx"],
                "ry": s["ry"],
                "color": s["color"],
                "alpha": int(alpha),
            }
        )
    return blobs, brightness_boost


def _advance_sparkle_state(params, t, fps, ctx, state):
    w, h = ctx["width"], ctx["height"]
    n_spots = params.get("spots", 20)
    base_radius = params.get("base_radius", 30)
    radius_var = params.get("radius_var", 15)
    base_alpha = params.get("base_alpha", 150)
    color = params.get("color", (255, 255, 255))
    if isinstance(color, list):
        color = tuple(color)
    edge_bias = params.get("edge_bias", 0.7)
    pulse_freq = params.get("pulse_freq", 8.0)
    decay = params.get("decay", 0.15)

    intensity = _sparkle_intensity(params, t, ctx)
    state[:] = [s for s in state if (t - s["birth_t"]) < decay]

    current_alive = len(state)
    available = max(0, n_spots - current_alive)
    desired = int(n_spots * min(intensity, 1.0))
    new_count = min(available, desired)
    if new_count > 0:
        np.random.seed(int(t * fps * 1000) % 2**16)
        for _ in range(new_count):
            x, y = _pick_sparkle_pos(w, h, edge_bias, params.get("central_exclusion", 0.35))
            r = base_radius + np.random.random() * radius_var
            r = r * (0.5 + 0.5 * intensity)
            max_alpha = base_alpha * intensity
            if pulse_freq > 0:
                max_alpha *= 0.5 + 0.5 * abs(
                    math.sin(t * pulse_freq * 2 * math.pi + np.random.random() * math.pi)
                )
            state.append(
                {
                    "birth_t": t,
                    "cx": int(x),
                    "cy": int(y),
                    "rx": int(r),
                    "ry": int(r),
                    "color": color,
                    "max_alpha": float(min(max_alpha, 255)),
                }
            )


def precompute_sparkle_lookup(params, n_frames, fps, ctx):
    """Precompute sparkle blobs per frame for parallel rendering."""
    state: list[dict] = []
    lookup: list[tuple[list, float]] = []
    for fi in range(n_frames):
        t = fi / fps
        _advance_sparkle_state(params, t, fps, ctx, state)
        lookup.append(_sparkle_blobs_from_state(params, t, state))
    return lookup


def _get_sparkle_blobs(params, t, ctx):
    sparkle_id = params.get("_sparkle_id")
    lookup = ctx.get("_sparkle_lookup")
    if sparkle_id is not None and lookup is not None and sparkle_id in lookup:
        fi = ctx.get("_frame_index", int(round(t * ctx.get("fps", 30))))
        fi = min(max(fi, 0), len(lookup[sparkle_id]) - 1)
        return lookup[sparkle_id][fi]

    fps = ctx.get("fps", 30)
    state_key = "_sparkle_state"
    if state_key not in ctx:
        ctx[state_key] = []
    state = ctx[state_key]
    _advance_sparkle_state(params, t, fps, ctx, state)
    ctx[state_key] = state
    return _sparkle_blobs_from_state(params, t, state)


def render_sparkle(params, frame, t, ctx):
    blobs, brightness_boost = _get_sparkle_blobs(params, t, ctx)
    if blobs:
        w, h = ctx["width"], ctx["height"]
        scale = ctx.get("blob_scale", 8)
        layer_arr = render_blob_layers(w, h, blobs, scale)
        layer_alpha = layer_arr[:, :, 3:4].astype(np.float32) / 255.0
        layer_rgb = layer_arr[:, :, :3].astype(np.float32)
        frame = np.clip(
            frame.astype(np.float32) + layer_rgb * layer_alpha * brightness_boost, 0, 255
        ).astype(np.uint16)
    return frame


RENDERERS = {
    "light_overlay": render_light_overlay,
    "spectrum": render_spectrum,
    "smoke": render_smoke,
    "text": render_text,
    "glitch": render_glitch,
    "bass_shake": render_bass_shake,
    "sparkle": render_sparkle,
}
