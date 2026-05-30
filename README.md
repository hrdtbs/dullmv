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

### Batch rendering

Apply one template DSL to every image/audio pair under `inputs/` and write `outputs/<name>.mp4` for each pair:

```bash
uv run python -m dullmv batch examples/template.dsl
```

Preview discovered jobs without rendering:

```bash
uv run python -m dullmv batch examples/template.dsl --dry-run
```

Skip pairs whose output already exists:

```bash
uv run python -m dullmv batch examples/template.dsl --skip-existing
```

#### Input layouts

**Subfolder (recommended):** each pair lives in its own folder. File names inside the folder can be anything as long as there is exactly one image and one audio file.

```
inputs/
  album_track_01/
    artwork.png
    mix.wav
  album_track_02/
    cover.jpg
    final.mp3
```

**Flat:** place files directly in `inputs/` with the same base name.

```
inputs/
  song01.png
  song01.wav
  song02.png
  song02.wav
```

By default, `dullmv batch` uses `--layout auto`: it prefers subfolder pairs when found, otherwise falls back to flat stem matching. Supported image extensions: `.png`, `.jpg`, `.jpeg`, `.webp`. Supported audio extensions: `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`.

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
pre-commit install
pre-commit run --all-files
```

## License

Private use. No license file is included.
