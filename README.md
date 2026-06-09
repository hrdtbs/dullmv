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
uv run pre-commit install
```

Or run both steps in one command:

```bash
uv run python scripts/setup_dev.py
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

### Batch rendering

Apply one template DSL to every image/audio pair under `inputs/` and write `outputs/<name>.mp4` for each pair:

```bash
uv run python -m dullmv batch examples/template.dsl
```

Preview discovered jobs without rendering:

```bash
uv run python -m dullmv batch examples/template.dsl --dry-run
```

Existing outputs are skipped by default. Re-render them with:

```bash
uv run python -m dullmv batch examples/template.dsl --no-skip-existing
```

#### Input layout

Place image and audio files directly in `inputs/` with the same base name:

```
inputs/
  song01.png
  song01.wav
  song02.jpg
  song02.mp3
```

This produces `outputs/song01.mp4` and `outputs/song02.mp4`. Subdirectories under `inputs/` are ignored.

Supported image extensions: `.png`, `.jpg`, `.jpeg`, `.webp`. Supported audio extensions: `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`.

The template DSL keeps its effect definitions; `base_image` and `audio` paths in the file are overridden per job at render time.

## Project layout

| Path | Description |
|------|-------------|
| `src/dullmv/` | Python package (`parser`, `engine`, `generator`, `batch`, CLI) |
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
uv run pre-commit run --all-files
```

Re-register Git hooks after cloning on a new machine or if hooks were removed:

```bash
uv run pre-commit install
```

## License

Private use. No license file is included.
