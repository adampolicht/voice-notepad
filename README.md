# Voice Notepad

Speak into your mic, get editable text in a local notepad. Fully local dictation (Polish + English),
powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper): no cloud, no accounts, no telemetry.

## Requirements

- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (`brew install uv`).
- A microphone and any modern browser.
- No ffmpeg needed (audio is decoded by PyAV). GPU optional; CPU works fine.

## Run

```bash
uv sync --extra dev          # install deps
cp .env.example .env         # optional: change model / language
uv run uvicorn app.main:app  # http://127.0.0.1:8000
```

Open the page, allow the mic, press record (or the spacebar), speak, press again to stop.

## The model: downloaded once, then offline

On **first run** the app downloads the chosen Whisper model from Hugging Face into
`~/.cache/huggingface` (default `small`, ~250 MB). This is the **only** time it touches the internet.

**Every run after that works fully offline** : audio and text never leave your machine. To pre-fetch the
model or force offline mode:

```bash
# download once while online
uv run python -c "from faster_whisper import WhisperModel; WhisperModel('small')"

# then run without any network access
HF_HUB_OFFLINE=1 uv run uvicorn app.main:app
```

The cached model is a local file: to run offline on another machine, copy `~/.cache/huggingface` there or
download it on that machine once.

## Configuration (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `WHISPER_MODEL` | `small` | `tiny` `base` `small` `medium` `large-v3` `large-v3-turbo`. Polish needs `small`+ ; `tiny`/`base` are weak |
| `WHISPER_DEVICE` | `auto` | `auto` picks CUDA if present, else CPU |
| `WHISPER_COMPUTE_TYPE` | `auto` | `int8` on CPU, `float16` on GPU |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Local only |
| `DEFAULT_LANGUAGE` | `auto` | `auto` `pl` `en` |

## Privacy

Everything runs on your machine. The server binds `127.0.0.1` only (not reachable from other devices),
and the one-time model download above is the sole outbound request. Notepad text is cached in the
browser's `localStorage`; use **Clear** to wipe it.

## Troubleshooting

- **Mic blocked:** re-allow the mic for `127.0.0.1:8000` in the browser and reload.
- **"Loading model…" stuck:** first run is still downloading, watch the terminal; record enables when ready.
- **Slow:** use a smaller model or a GPU (`WHISPER_DEVICE` shows the active device in the terminal).
- **Wrong language on short clips:** pick Polski/English explicitly instead of Auto-detect.

## Development

```bash
uv run pytest                    # fast, offline (model is mocked)
RUN_INTEGRATION=1 uv run pytest  # real model against the fixtures
uv run ruff check
```

See `SPEC.md` for the full spec and `docs/DECISIONS.md` for build decisions.
