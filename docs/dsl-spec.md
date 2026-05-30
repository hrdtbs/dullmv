# Effect DSL Specification

## 1. Overview

This document describes the custom text DSL (Domain Specific Language) used to define video effects.
A `.dsl` file is parsed by `dullmv.parser` and rendered by `dullmv.generator` through `dullmv.engine`.

Run the renderer with:

```bash
uv run python -m dullmv examples/test.dsl
```

By default, output is written to `outputs/<dsl-stem>.mp4` under the project root. Use `-o` / `--output` to override.

### Project Layout

| Path | Purpose |
|------|---------|
| `examples/` | Sample `.dsl` files |
| `inputs/` | Source media (images, audio) — gitignored |
| `outputs/` | Rendered MP4 files — gitignored |
| `src/dullmv/` | Python package |
| `docs/dsl-spec.md` | This specification |

Media paths inside a DSL file are resolved **relative to the DSL file**. Example DSL files reference assets with `../inputs/Bloom.png`.

---

## 2. File Structure

A DSL file consists of two sections:

1. **Global Settings** — top-level key/value pairs.
2. **Effect Blocks** — one or more `effect <name> { ... }` blocks.

```
# Comment starts with '#'
<key> <value>
<key> <value>

effect <effect_name> {
    <key> <value>
    <sub_block> {
        <key> <value>
    }
}
```

Blocks are delimited by `{` and `}`.
Indentation is optional and ignored.

---

## 3. Value Types

The parser supports the following literal forms:

| Type | Syntax | Example |
|------|--------|---------|
| Integer | bare number | `30`, `1280` |
| Float | bare number with `.` | `12.0`, `0.35` |
| String | double-quoted | `"Bloom.png"`, `"ease_out_cubic"` |
| Tuple | comma-separated inside `()` | `(255, 245, 250)`, `(-600, 400)` |
| Relative tuple | `float` in `0.0~1.0` inside `()` | `(0.094, 0.167)` — auto-scaled by `width`/`height` |
| Expression | double-quoted string evaluated at runtime | `"sin(t * 0.6 + index)"` |
| List (auto) | comma-separated values | `1, 2, 3` (parsed as `[1, 2, 3]`) |

**Note:** Strings that look like Python expressions are treated as expressions and evaluated per-frame using a restricted `eval` environment.

### Relative Coordinates (0.0 ~ 1.0)

For coordinate parameters such as `anchor`, `start_pos`, and `end_pos`, you may specify values as either:

- **Absolute pixels:** integer or float > 1.0 — e.g. `(120, 400)`
- **Relative ratios:** float in the range `0.0` ~ `1.0` — e.g. `(0.094, 0.556)`

When a tuple element is a `float` between `0.0` and `1.0` (inclusive), the engine automatically multiplies it by `width` (for X) or `height` (for Y) at render time. This makes the effect resolution-independent — changing `size` does not require rewriting blob positions or text coordinates.

**Example:**
```
# At 1280x720, (0.094, 0.167) becomes approximately (120, 120)
anchor (0.094, 0.167)

# Negative relative values also work (off-screen to the left)
start_pos (-0.469, 0.556)
```

---

## 4. Global Settings

Top-level keys outside any `effect` block. All paths are relative to the `.dsl` file's directory.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `size` | tuple `(w, h)` | `(1920, 1080)` | Output resolution in pixels. |
| `fps` | int | `30` | Frames per second. |
| `duration` | float | *(auto)* | Total video duration in seconds. If omitted, the length of the `audio` file is used automatically. |
| `opening_duration` | float | `3.0` | Duration of the opening text phase. |
| `base_image` | string | `"Bloom.png"` | Background image file path. |
| `audio` | string | `"Bloom.wav"` | Audio file path. |
| `blob_scale` | int | `8` | Downscale factor for blob rendering optimization. |
| `beat_decay` | float | `0.35` | Beat intensity decay time in seconds. |
| `preset` | string | `"medium"` | x264 encoding preset. Slower presets yield better compression. Options: `"ultrafast"`, `"superfast"`, `"veryfast"`, `"faster"`, `"fast"`, `"medium"`, `"slow"`, `"slower"`, `"veryslow"`. |
| `workers` | int | *(CPU count)* | Parallel processes for frame generation. Use `1` to force single-threaded rendering. |
| `threads` | int | *(CPU count)* | FFmpeg encoder thread count. |
| `font` | string | `"C:\\Windows\\Fonts\\impact.ttf"` | Font file path for text effects. |
| `font_size` | int | `140` | Font size for text effects. |

---

## 5. Expression Evaluation

Any string value is evaluated as a Python expression at **frame generation time**.

### Available Variables

| Variable | Description |
|----------|-------------|
| `t` | Current time in seconds. |
| `width` | Frame width in pixels. |
| `height` | Frame height in pixels. |
| `index` | Zero-based index within the containing list (e.g., blob index). |
| `anchor_x` | X coordinate of the blob's `anchor`. |
| `anchor_y` | Y coordinate of the blob's `anchor`. |
| `dist_ratio` | Normalized distance from center (0.0~1.0), computed automatically in `smoke` blobs. |

### Available Functions

| Function | Description |
|----------|-------------|
| `sin(x)`, `cos(x)`, `tan(x)` | Trigonometric functions (radians). |
| `sqrt(x)` | Square root. |
| `pow(x, y)` | Power. |
| `abs(x)` | Absolute value. |
| `min(...)`, `max(...)` | Minimum / maximum. |
| `int(x)`, `float(x)` | Type conversion. |
| `round(x)` | Rounding. |
| `random()` | Random float in `[0.0, 1.0)`. |
| `seed(x)` | Set random seed. |
| `radians(x)`, `degrees(x)` | Angle conversion. |
| `exp(x)`, `log(x)` | Exponential / natural logarithm. |
| `ceil(x)`, `floor(x)` | Ceiling / floor. |
| `pi` | Mathematical constant π. |
| `beat_intensity(decay=0.35)` | Returns beat proximity intensity (0.0~1.0). Available only when audio analysis is enabled. |

### Example Expressions

```
"80 + 50 * sin(t * 0.6 + index)"
"(140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + index * 0.8))"
"int(25 + dist_ratio * 90)"
"8 + random() * 12"
"(random() - 0.5) * 10"
```

---

## 6. Effect Definitions

Each effect is declared as:

```
effect <effect_name> {
    ...
}
```

Effects are applied in the order they appear in the file.

---

### 6.1 `light_overlay`

Renders soft Gaussian-like light blobs drifting in circular patterns.

**Sub-block:** `blob { }` (repeatable)

| Parameter | Type | Description |
|-----------|------|-------------|
| `anchor` | tuple `(x, y)` | Base position for drift calculation. Supports **relative** `0.0~1.0` floats (see §3). |
| `color` | tuple `(r, g, b)` | Blob color. |
| `cx` | expression / int | Center X (evaluated per frame). Use `anchor_x` to follow the resolved anchor. |
| `cy` | expression / int | Center Y (evaluated per frame). Use `anchor_y` to follow the resolved anchor. |
| `rx` | expression / int | Horizontal radius (evaluated per frame). |
| `ry` | expression / int | Vertical radius (evaluated per frame). |
| `alpha` | expression / int | Alpha intensity (0~255). |

---

### 6.2 `spectrum`

Renders audio spectrum bars at the bottom of the frame.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bars` | int | `96` | Number of frequency bars. |
| `max_height_ratio` | float | `0.35` | Maximum bar height as a ratio of frame height. |
| `color` | tuple `(r, g, b)` | `(255, 255, 255)` | Bar color. |
| `alpha` | int | `150` | Bar alpha (0~255). |
| `boost` | float | `1.2` | Height boost multiplier. |

---

### 6.3 `smoke`

Renders colored soft blobs that drift using multi-frequency sinusoidal motion.

**Sub-block:** `blob { }` (repeatable)

| Parameter | Type | Description |
|-----------|------|-------------|
| `anchor` | tuple `(x, y)` | Base position for drift calculation. Supports **relative** `0.0~1.0` floats (see §3). |
| `color` | tuple `(r, g, b)` | Blob color. |
| `cx` | expression / int | Center X (evaluated per frame). Use `anchor_x` to follow the resolved anchor. |
| `cy` | expression / int | Center Y (evaluated per frame). Use `anchor_y` to follow the resolved anchor. |
| `rx` | expression / int | Horizontal radius (evaluated per frame). |
| `ry` | expression / int | Vertical radius (evaluated per frame). |
| `alpha` | expression / int | Alpha intensity (0~255). |

**Auto-computed variable:** `dist_ratio` — normalized distance of the blob from the screen center.

---

### 6.4 `text`

Renders sliding/fading text during the opening phase (`t < opening_duration`).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `color` | tuple `(r, g, b)` | `(255, 255, 255)` | Text color. |
| `fade_out_start` | float | `2.0` | Time (seconds) when fade-out begins. |
| `fade_out_duration` | float | `1.0` | Fade-out duration in seconds. |

**Sub-block:** `line { }` (repeatable)

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | string | Display text. |
| `start_time` | float | When this line starts animating. |
| `slide_duration` | float | Duration of the slide-in motion. |
| `fade_duration` | float | Duration of the fade-in. |
| `start_pos` | tuple `(x, y)` | Starting position. Supports **relative** `0.0~1.0` floats (see §3). |
| `end_pos` | tuple `(x, y)` | Ending position. Supports **relative** `0.0~1.0` floats (see §3). |
| `easing` | string | Easing name. Supported: `"ease_out_cubic"`, `"linear"`. |

---

### 6.5 `glitch`

Applies horizontal slice-shift glitch artifacts in the corners with a random probability.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `probability` | float | `0.10` | Chance (0.0~1.0) to trigger glitch per frame. |
| `corner_ratio` | float | `0.22` | Corner rectangle size ratio. |
| `max_waves` | int | `2` | Maximum number of wave shifts per corner. |
| `min_shift` | int | `2` | Minimum absolute shift to apply. |
| `wave_height` | expression / int | `"8 + random() * 12"` | Height of each glitch wave slice. |
| `base_shift` | expression / int | `"(random() - 0.5) * 10"` | Base horizontal shift amount. |

---

### 6.6 `bass_shake`

Applies bass-onset-driven camera shake with optional RGB chromatic split. Shift values are precomputed at startup from the bass intensity curve.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `amount` | float | `18` | Shake amplitude multiplier. |
| `direction` | string | `"both"` | Shake axis: `"horizontal"`, `"vertical"`, or `"both"`. |
| `decay` | float | `0.4` | Onset impulse decay time in seconds. |
| `oscillation_freq` | float | `14.0` | Oscillation frequency for shake and RGB split. |
| `rgb_split` | int | `5` | RGB channel offset in pixels (0 disables split). |
| `idle_amount` | float | `2.5` | Micro-shake amplitude during sustained bass. |
| `idle_freq` | float | `3.0` | Micro-shake frequency. |
| `y_ratio` | float | `1.0` | Vertical shake multiplier relative to horizontal. |
| `zoom` | float | *(ignored)* | Reserved; zoom shake is not applied at runtime. |

---

### 6.7 `sparkle`

Renders additive sparkle blobs driven by bass intensity. Sparkles spawn near frame edges, decay over time, and are composited additively on top of prior effects.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `spots` | int | `20` | Maximum simultaneous sparkles on screen. |
| `base_radius` | int | `30` | Base blob radius in pixels. |
| `radius_var` | int | `15` | Random radius variation. |
| `base_alpha` | int | `150` | Base alpha (0~255). |
| `color` | tuple `(r, g, b)` | `(255, 255, 255)` | Sparkle color. |
| `edge_bias` | float | `0.7` | Probability (0~1) to spawn near frame edges. |
| `threshold` | float | `0.05` | Minimum bass intensity to spawn (legacy; spawning uses intensity directly). |
| `intensity_scale` | float | `1.5` | Bass intensity multiplier. |
| `pulse_freq` | float | `8.0` | Alpha pulse frequency. |
| `decay` | float | `0.15` | Sparkle lifetime in seconds. |
| `central_exclusion` | float | `0.35` | Excluded central region ratio (0~1). |
| `brightness_boost` | float | `2.5` | Additive blend multiplier. |
| `fade_mode` | string | `"exponential"` | Fade curve: `"exponential"` or `"linear"`. |
| `alpha_cutoff` | float | `0.0` | Skip blobs below this alpha. |

---

## 7. Easing Functions

Available easing names for the `text` effect:

| Name | Description |
|------|-------------|
| `ease_out_cubic` | `1 - (1 - x)^3` |
| `linear` | `x` (no easing) |

---

## 8. Complete Example

```
# Global settings
size 1920 1080
fps 30
opening_duration 3.0
base_image "../inputs/Bloom.png"
audio "../inputs/Bloom.wav"
blob_scale 8
beat_decay 0.35
preset "medium"
font "C:\\Windows\\Fonts\\impact.ttf"
font_size 140

# Light Overlay
effect light_overlay {
    blob {
        anchor (0.094, 0.167)
        color (255, 245, 250)
        cx "int(max(100, min(width - 100, anchor_x + (80 + 50 * sin(t * 0.6 + 0)) * cos(radians((t * 20) % 360 + 0 * 90)))))"
        cy "int(max(100, min(height - 100, anchor_y + (80 + 50 * sin(t * 0.6 + 0)) * sin(radians((t * 20) % 360 + 0 * 90)))))"
        rx "int(180 * (0.9 + 0.1 * sin(t * 0.9 + 0)))"
        ry "int(120 * (0.9 + 0.1 * cos(t * 0.8 + 0)))"
        alpha 110
    }
    # ... more blobs using relative anchors
}

# Spectrum Bars
effect spectrum {
    bars 96
    max_height_ratio 0.35
    color (255, 255, 255)
    alpha 150
    boost 1.2
}

# Colored Smoke
effect smoke {
    blob {
        anchor (0.094, 0.167)
        color (255, 248, 252)
        cx "int(max(80, min(width - 80, anchor_x + 50 * sin(t * (1.6 + 0 * 0.20) + 0 * 1.1 + 0.3) + 30 * cos(t * (0.48 + 0 * 0.08) + 0 * 1.7 + 0.5))))"
        cy "int(max(80, min(height - 80, anchor_y + 50 * cos(t * (1.40 + 0 * 0.16) + 0 * 1.1 + 0.3) + 25 * sin(t * (0.36 + 0 * 0.06) + 0 * 1.7 + 0.5))))"
        rx "int((140 + 70 * dist_ratio) * (0.95 + 0.05 * sin(t * 0.6 + 0 * 0.8)))"
        ry "int((100 + 50 * dist_ratio) * (0.95 + 0.05 * cos(t * 0.5 + 0 * 1.1)))"
        alpha "int(25 + dist_ratio * 90)"
    }
    # ... more blobs using relative anchors
}

# Opening Text
effect text {
    color (255, 255, 255)
    fade_out_start 2.0
    fade_out_duration 1.0

    line {
        text "TITLE LINE ONE"
        start_time 0.0
        slide_duration 0.9
        fade_duration 0.6
        start_pos (-0.469, 0.556)
        end_pos (0.062, 0.556)
        easing "ease_out_cubic"
    }
    line {
        text "TITLE LINE TWO"
        start_time 0.35
        slide_duration 0.9
        fade_duration 0.6
        start_pos (-0.391, 0.750)
        end_pos (0.062, 0.750)
        easing "ease_out_cubic"
    }
}

# Glitch
effect glitch {
    probability 0.10
    corner_ratio 0.22
    max_waves 2
    min_shift 2
    wave_height "8 + random() * 12"
    base_shift "(random() - 0.5) * 10"
}

# Bass Shake
effect bass_shake {
    amount 4
    direction both
    decay 0.4
    oscillation_freq 7.0
    rgb_split 2
    idle_amount 1
    idle_freq 1.0
    y_ratio 2
}

# Sparkle
effect sparkle {
    spots 4
    base_radius 25
    radius_var 20
    base_alpha 200
    color (255, 255, 255)
    edge_bias 0.8
    intensity_scale 2.0
    pulse_freq 10.0
    decay 0.35
    central_exclusion 0.4
    brightness_boost 3.5
    fade_mode "exponential"
}
```

---

## 9. Tips

- **Effect ON/OFF:** Comment out or delete the entire `effect <name> { ... }` block.
- **Reorder:** Move `effect` blocks up or down to change compositing order.
- **Parameter Tuning:** Edit numbers or expressions without restarting the Python interpreter.
- **Path Resolution:** `base_image`, `audio`, and `font` paths are resolved relative to the `.dsl` file location. In this repo, place media in `inputs/` and reference it from `examples/` with `../inputs/...`.
- **Default Output:** Unless `-o` is passed, rendered videos go to `outputs/<dsl-stem>.mp4` under the project root.
- **Resolution Independence:** Use **relative coordinates** (`0.0~1.0`) for `anchor`, `start_pos`, and `end_pos`. This guarantees that changing `size` (e.g. from `1280 720` to `1920 1080`) does not require rewriting blob positions or text coordinates. Combined with using `anchor_x` / `anchor_y` inside expressions, the entire effect layout scales automatically.
