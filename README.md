# Voice Notepad

A personal, fully local dictation tool: speak into your microphone and the transcribed text lands in an
editable notepad you can tidy up and copy anywhere. Everything runs on your own machine — Polish and
English — powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper); no cloud, no accounts,
no telemetry.

## Prerequisites

- **Python 3.11+** (developed on 3.12).
- **[uv](https://docs.astral.sh/uv/)** for dependency management (`brew install uv`, or see their docs).
  A `pip` + `requirements` flow works too, but the commands below assume `uv`.
- **A microphone**, and a browser that supports `MediaRecorder` (Chrome, Edge, Opera, Firefox, Safari 14.1+).
- **No ffmpeg needed.** Audio is decoded by PyAV, which bundles its own ffmpeg. (If you ever hit a decode
  error, installing a system ffmpeg — `brew install ffmpeg` — is a safe fallback.)
- **GPU is optional.** Runs fine on CPU; a CUDA GPU just makes larger models faster.

## Install & run

```bash
uv sync --extra dev          # create the venv and install deps
cp .env.example .env         # optional: adjust model / device / language
uv run uvicorn app.main:app  # starts on http://127.0.0.1:8000
```

Open **http://127.0.0.1:8000**, allow microphone access when prompted, press the round record button
(or hit the spacebar), speak, and press it again to stop. The text appears in the notepad.

> First launch downloads the chosen Whisper model from Hugging Face (once). After that it runs offline —
> see [Offline use](#offline-use).

## Configuration

Set via `.env` (copied from `.env.example`; `.env` is git-ignored):

| Variable | Default | Values | Notes |
|---|---|---|---|
| `WHISPER_MODEL` | `small` | `tiny` `base` `small` `medium` `large-v3` `large-v3-turbo` | Bigger = more accurate, slower |
| `WHISPER_DEVICE` | `auto` | `auto` `cpu` `cuda` | `auto` picks CUDA if present, else CPU |
| `WHISPER_COMPUTE_TYPE` | `auto` | `auto` `int8` `float16` `float32` | `auto` → `float16` on GPU, `int8` on CPU |
| `HOST` | `127.0.0.1` | — | Kept local; do not expose publicly |
| `PORT` | `8000` | — | |
| `DEFAULT_LANGUAGE` | `auto` | `auto` `pl` `en` | Default for the language dropdown |

## Model size vs. speed & quality

| Model | Rough size | CPU speed | Quality (esp. Polish) |
|---|---|---|---|
| `tiny` / `base` | ~75 / 145 MB | fastest | weak Polish — diacritics/words slip |
| `small` | ~250 MB | good on a modern laptop | **recommended minimum** for Polish |
| `medium` | ~770 MB | slow on CPU | strong |
| `large-v3` / `large-v3-turbo` | ~1.5 GB | GPU recommended | best; `-turbo` is much faster |

Guidance:
- **CPU-only laptop →** start with `small` (or `base` if you only need English and want speed).
- **Decent GPU →** `large-v3-turbo` or `large-v3` for the best Polish accuracy.
- Polish quality drops noticeably on `tiny`/`base`; `small` is the floor.

On a typical modern laptop a 30-second clip transcribes in well under 30 seconds with `small` on CPU.

## Privacy

- Audio and transcribed text **never leave your machine**. There are no accounts, analytics, or outbound
  requests at runtime.
- The **only** network access is a one-time model download from Hugging Face on first run.
- The server binds `127.0.0.1` only — it is not reachable from other devices.
- The notepad text is cached in your browser's `localStorage` (local to your machine) so a refresh doesn't
  lose it. Use **Clear** to wipe it.

### Offline use

Pre-download the model once while online, then run with the network off:

```bash
# Downloads and caches the model into ~/.cache/huggingface
uv run python -c "from faster_whisper import WhisperModel; WhisperModel('small')"
```

Subsequent runs work fully offline. To force offline mode explicitly, set `HF_HUB_OFFLINE=1`.

## Troubleshooting

- **Microphone blocked / denied.** The UI shows a clear message. Re-enable mic access for
  `127.0.0.1:8000` in your browser's site settings, then reload. Browsers only allow the mic on
  `localhost`/`127.0.0.1` or HTTPS — `http://127.0.0.1:8000` counts as a secure context, so no
  certificates are required.
- **"Loading model…" won't finish.** First run is downloading the model; watch the terminal. The record
  button enables automatically once `/api/health` reports `ok`.
- **Transcription is slow.** Use a smaller model (`base`/`small`) or a GPU. Check the terminal for the
  active `device` — CPU with a large model is the usual cause.
- **Wrong language detected** (common on very short clips). Pick **Polski** or **English** explicitly in
  the dropdown instead of Auto-detect.
- **CUDA not found / falls back to CPU.** Expected without an NVIDIA GPU + CUDA libraries. Force it with
  `WHISPER_DEVICE=cpu` to silence probing, or install the CUDA runtime for GPU speed.
- **Audio decode error.** Rare; install a system ffmpeg (`brew install ffmpeg`) as a fallback.

## Development

```bash
uv run pytest                 # fast, offline (API tests mock the model)
RUN_INTEGRATION=1 uv run pytest  # also runs the real-model test against the fixtures
uv run ruff check             # lint
```

See `SPEC.md` for the full spec and `docs/DECISIONS.md` for choices made along the way.
