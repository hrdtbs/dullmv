# dullmv

DSL-driven music video generator. Define effects, timing, and parameters in a `.dsl` file and render an MP4 without editing Python code.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [FFmpeg](https://ffmpeg.org/) (used by MoviePy for H.264/AAC encoding)

## Setup

```bash
git clone <repository-url>
cd dullmv
uv sync --all-extras
```

### Input media

Place source images and audio in `inputs/`. This directory is gitignored.

For the bundled examples, copy or symlink sample assets:

```bash
# After cloning, if inputs/ is empty:
cp /path/to/Bloom.png inputs/
cp /path/to/Bloom.wav inputs/
```

The example DSL files in `examples/` reference `../inputs/Bloom.png` and `../inputs/Bloom.wav`.

## Usage

Render the sample project:

```bash
uv run python -m dullmv examples/test.dsl
```

Output is written to `outputs/test.mp4` by default.

Custom output path:

```bash
uv run python -m dullmv examples/template.dsl -o outputs/custom.mp4
```

## Project layout

| Path | Description |
|------|-------------|
| `src/dullmv/` | Python package (`parser`, `engine`, `generator`, CLI) |
| `examples/` | Sample `.dsl` files |
| `inputs/` | Source media (gitignored) |
| `outputs/` | Rendered videos (gitignored) |
| `docs/dsl-spec.md` | Effect DSL specification |
| `tests/` | Unit tests |

## DSL overview

A DSL file has global settings (resolution, fps, media paths) and ordered `effect` blocks:

```dsl
size 1280 720
fps 30
base_image "../inputs/Bloom.png"
audio "../inputs/Bloom.wav"

effect spectrum {
    bars 96
    color (255, 255, 255)
    alpha 150
}
```

Supported effects: `light_overlay`, `spectrum`, `smoke`, `text`, `glitch`, `bass_shake`, `sparkle`.

See [docs/dsl-spec.md](docs/dsl-spec.md) for the full specification.

## Font paths

The `font` global setting is OS-specific. Examples use Windows Impact:

```dsl
font "C:\\Windows\\Fonts\\impact.ttf"
```

On macOS, a common alternative is `/System/Library/Fonts/Supplemental/Impact.ttf`. On Linux, install a compatible font and point `font` to its path.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
pre-commit install
pre-commit run --all-files
```

## License

Private use. No license file is included.
