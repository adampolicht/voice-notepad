# CLAUDE.md

Personal, fully local voice-to-text notepad. See `SPEC.md` for full scope and acceptance criteria.

## Conventions
- Python 3.11+, type hints on all functions, docstrings only where intent isn't obvious.
- One responsibility per module; no premature abstractions.
- Keep it small: aim for < ~400 lines of application code.
- Commit messages in imperative mood, one logical change per commit.
- Never commit `.env`, model weights, or recorded audio (only the two tiny test fixtures).
- Server binds `127.0.0.1` only, never `0.0.0.0`.
- No cloud calls at runtime (except one-time model download on first run).

## Layout
- `app/main.py` — FastAPI app, routes, startup model load.
- `app/transcriber.py` — faster-whisper wrapper.
- `app/config.py` — env loading.
- `app/static/index.html` — single-file UI.
- `tests/` — pytest (API tests mock the transcriber; no model download in CI).
- `docs/DECISIONS.md` — decisions taken where the spec was ambiguous.

## Run
- `uv sync --extra dev`
- `uv run uvicorn app.main:app` → http://127.0.0.1:8000
- `uv run pytest` / `uv run ruff check`
