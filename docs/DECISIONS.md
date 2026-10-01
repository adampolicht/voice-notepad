# Decisions

Choices made where the spec left room, kept intentionally small.

- **Python 3.12 via Homebrew.** The machine's system Python is 3.9; used `/opt/homebrew/bin/python3.12` for the `.venv` to satisfy the `>=3.11` requirement.
- **uv as dependency manager.** Matches the acceptance criteria (`uv sync`, `uv run`). `uv.lock` is committed for reproducibility.
- **No system ffmpeg.** faster-whisper decodes audio via PyAV, which bundles its own ffmpeg, so browser webm/opus decodes without a system ffmpeg install. Documented in README troubleshooting.
- **Config via pydantic-settings.** Small, typed, reads `.env` automatically. `WHISPER_*` env vars map to snake_case fields.
- **`compute_type=auto`** resolves to `float16` on CUDA and `int8` on CPU (the fast, low-memory default). Overridable via env.
- **API tests mock the transcriber.** Keeps `pytest` fast and offline (no model download in test runs). A separate, opt-in integration test uses the real model against the fixtures and is skipped unless `RUN_INTEGRATION=1`.
- **Test fixtures generated with macOS `say` + `afconvert`** (16 kHz mono WAV). They are tiny and committed so tests and manual checks are reproducible.
- **Append vs. replace** implemented as a UI toggle; default append with a blank line between entries, per FR-4.
- **Notes as one JSON file each.** A saved notes library (sidebar like Claude/ChatGPT chats) persists server-side. Each note is a single JSON file (`<uuid>.json`) in `NOTES_DIR` (default `~/.voice-notepad/notes`, outside the repo), written atomically via a temp file + rename. Chosen over a database for zero deps, human-readable files, and easy backup. Note ids are 32-char hex (uuid4) and validated against a regex before touching the filesystem, so a request id can't traverse out of the notes dir.
- **Auto-tracked titles.** A note's title follows its first non-empty line until the user explicitly renames it (a `renamed` flag then pins the manual title). Mirrors how chat apps name conversations without a separate title field in the UI.
- **Client autosave, debounced.** The editor PUTs content 600 ms after the last keystroke (and on blur / `beforeunload` via `fetch(keepalive)`), replacing the old single-buffer `localStorage` persistence. Only language and insert-mode prefs remain in `localStorage`.
