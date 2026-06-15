# dullmv

CapCut template-driven music video generator. Duplicate a CapCut draft template, swap image/audio/text slots from `inputs/`, and export MP4 via the CapCut desktop app.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- **Windows** with [CapCut](https://www.capcut.com/) (international edition) installed
- A CapCut **template draft** saved locally (see below)

## Setup

```bash
git clone <repository-url>
cd dullmv
uv sync --all-extras
uv run pre-commit install
```

Or:

```bash
uv run python scripts/setup_dev.py
```

## CapCut template preparation

1. Design your music video template in CapCut (effects, transitions, text styles, etc.).
2. Save it as a draft and note its name as shown on the CapCut home screen.
3. Find your drafts folder: CapCut → **Settings** → **Drafts Location**  
   Typical path: `C:\Users\<you>\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft`
4. Identify **material names** inside the template (usually the original file names, e.g. `cover.png`, `bgm.wav`).  
   Use CapCut’s material panel or inspect the draft with `pycapcut` if needed.

Copy [`templates/default.yaml`](templates/default.yaml) and set:

- `drafts_dir` — your CapCut drafts folder (or set `CAPCUT_DRAFTS_DIR`)
- `template_name` — exact draft name in CapCut
- `slots.image` / `slots.audio` — material names to replace
- `slots.texts` — optional text segment overrides

## Input media

Place source images and audio in `inputs/` (gitignored):

```
inputs/
  song01.png
  song01.wav
  song02.jpg
  song02.mp3
```

Supported images: `.png`, `.jpg`, `.jpeg`, `.webp`  
Supported audio: `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`

## Usage

**Before rendering:** open CapCut on the **drafts home screen** and leave it running. Do not interact with CapCut during export.

### Single render

With one image/audio pair in `inputs/`:

```bash
uv run python -m dullmv render templates/default.yaml
```

Explicit paths:

```bash
uv run python -m dullmv render templates/default.yaml \
  --image inputs/song01.png \
  --audio inputs/song01.wav \
  -o outputs/song01.mp4
```

Build draft only (no UI export):

```bash
uv run python -m dullmv render templates/default.yaml --skip-export
```

### Batch rendering

```bash
uv run python -m dullmv batch templates/default.yaml
```

Preview jobs:

```bash
uv run python -m dullmv batch templates/default.yaml --dry-run
```

Re-render existing outputs:

```bash
uv run python -m dullmv batch templates/default.yaml --no-skip-existing
```

## How it works

dullmv uses [`pycapcut`](https://github.com/GuanYixuan/pyCapCut) directly (no separate capcut-mate/cutauto servers):

1. **Duplicate** the template draft in your CapCut drafts folder
2. **Replace** image, audio, and text slots via `replace_material_by_name` / `replace_text`
3. **Save** `draft_content.json`
4. **Export** MP4 by automating the CapCut desktop UI (`uiautomation`)

## Project layout

| Path | Description |
|------|-------------|
| `src/dullmv/capcut/` | Config, draft builder, export controller, pipeline |
| `templates/` | YAML template configs |
| `inputs/` | Source media (gitignored) |
| `outputs/` | Rendered videos (gitignored) |
| `tests/` | Unit tests |

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

Integration tests against real CapCut are skipped in CI. To run locally with CapCut open, use `--skip-export` for draft-only checks.

## Limitations

- CapCut UI export is **serial only** (one job at a time).
- Template drafts must use an **unencrypted** `draft_content.json` (template mode limitation in `pycapcut`).
- Material names in YAML must **exactly match** names inside the CapCut template.
- Unofficial automation; CapCut updates may break export.

## License

Private use. No license file is included.
