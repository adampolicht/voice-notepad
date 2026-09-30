# Local Voice-to-Text Tool (MVP) — Project Spec

> Hand this file to Claude Code in an empty repo. It is the source of truth for scope, stack, and acceptance criteria. If something is ambiguous, pick the simplest option that satisfies the MVP and note the decision in `docs/DECISIONS.md`.

## 1. Goal

A personal, fully local dictation tool: I speak into my microphone, and the transcribed text appears in a simple notepad-style text area where I can edit it and copy/paste it elsewhere.

- Single user, runs on my own machine only.
- No cloud APIs, no accounts, no telemetry. Audio and text never leave the machine.
- Languages: **Polish (pl)** and **English (en)**. Nothing else needs to work well.
- Simpler than Whisper-based products: no diarization, no subtitles, no batch pipelines.

## 2. Non-goals (for the MVP)

- No multi-user support, auth, or deployment.
- No real-time word-by-word streaming (record → stop → transcribe is fine).
- No system-wide hotkey, no auto-typing into other apps (see Roadmap).
- No training or fine-tuning of models.
- No packaging into an installer.

## 3. Tech Stack

| Concern | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** | Best ecosystem for local speech models |
| Speech-to-text | **faster-whisper** (CTranslate2 build of OpenAI Whisper) | Runs locally, fast on CPU and GPU, good Polish accuracy |
| Backend | **FastAPI** + Uvicorn | Small, typed, easy to test |
| Frontend | One static `index.html` (vanilla JS, no build step) | Browser `MediaRecorder` handles mic capture; zero tooling |
| Dependency mgmt | **uv** (fallback: `pip` + `requirements.txt`) | Fast, reproducible |
| Tests | `pytest` | |
| Lint/format | `ruff` | |
| Repo | GitHub, `main` branch, small focused commits | |

Server binds to `127.0.0.1` only — never `0.0.0.0`.

Note: browsers only allow microphone access on `localhost` or HTTPS. `http://127.0.0.1:8000` counts as secure context, so no certificates are needed.

### Alternative (only if the above blocks progress)
Gradio with `gr.Audio(sources=["microphone"])` + `gr.Textbox`. Faster to build, less control over UI. Do not use unless FastAPI approach fails.

## 4. Functional Requirements

### FR-1 Record audio
- A large **Record / Stop** button toggles recording.
- Visible recording state (color change + elapsed timer).
- Browser asks for microphone permission on first use.

### FR-2 Transcribe locally
- On Stop, the audio blob is POSTed to `POST /api/transcribe`.
- Backend transcribes with faster-whisper and returns JSON: `{ "text": str, "language": str, "duration_s": float, "processing_s": float }`.
- Model is loaded **once at startup** (not per request) and kept in memory.

### FR-3 Language control
- Dropdown with: **Auto-detect**, **Polski**, **English**. Default: Auto-detect.
- When a language is chosen explicitly, pass it to the model (more accurate than auto for short clips).
- Display the detected language next to the result.

### FR-4 Notepad
- A large editable `<textarea>` is the main UI element.
- New transcriptions are **appended** at the cursor end, separated by a blank line (setting: append vs. replace).
- Buttons: **Copy all**, **Clear**.
- Text auto-saves to `localStorage` so a page refresh doesn't lose it.

### FR-5 Status & errors
- Show states: idle, recording, transcribing (spinner), done.
- Clear, human-readable errors: mic denied, model still loading, empty/silent audio, server unreachable.
- `GET /api/health` returns `{ "status": "ok" | "loading", "model": str, "device": str }`. UI disables Record while `loading`.

## 5. Non-Functional Requirements

- **Privacy:** no outbound network calls at runtime, except the one-time model download from Hugging Face on first run (document this in README, plus how to pre-download for offline use).
- **Performance:** a 30-second clip should transcribe in well under 30 seconds on a typical modern laptop with the default model; document expected speeds per model in README.
- **Hardware-agnostic:** auto-select device (`cuda` if available, else `cpu`) with `compute_type` fallback (`float16` on GPU, `int8` on CPU). Everything overridable via env vars.
- **Simplicity:** aim for < ~400 lines of application code total for the MVP. No unnecessary abstractions.

## 6. Configuration

Via `.env` (with `.env.example` committed, `.env` git-ignored):

```
WHISPER_MODEL=small        # tiny | base | small | medium | large-v3 | large-v3-turbo
WHISPER_DEVICE=auto        # auto | cpu | cuda
WHISPER_COMPUTE_TYPE=auto  # auto | int8 | float16 | float32
HOST=127.0.0.1
PORT=8000
DEFAULT_LANGUAGE=auto      # auto | pl | en
```

Model guidance to put in README:
- CPU-only machine → start with `small` (or `base` for speed).
- Decent GPU → `large-v3-turbo` or `large-v3` for best Polish accuracy.
- Polish quality drops noticeably on `tiny`/`base`; recommend `small` as the minimum.

## 7. Suggested Repository Layout

```
voice-notepad/
├── README.md
├── SPEC.md                  # this file
├── CLAUDE.md                # short pointer + conventions for Claude Code
├── pyproject.toml
├── .env.example
├── .gitignore
├── app/
│   ├── main.py              # FastAPI app, routes, startup model load
│   ├── transcriber.py       # faster-whisper wrapper
│   ├── config.py            # env loading (pydantic-settings or plain os.environ)
│   └── static/
│       └── index.html       # UI (HTML + CSS + JS in one file)
├── tests/
│   ├── test_health.py
│   ├── test_transcribe.py
│   └── fixtures/
│       ├── hello_en.wav     # short English sample
│       └── czesc_pl.wav     # short Polish sample
└── docs/
    └── DECISIONS.md
```

## 8. API Contract

### `GET /` 
Serves `index.html`.

### `GET /api/health`
```json
{ "status": "ok", "model": "small", "device": "cpu" }
```

### `POST /api/transcribe`
- Request: `multipart/form-data`
  - `audio`: file (webm/opus, ogg, wav, mp3, m4a — whatever the browser sends)
  - `language`: `"auto" | "pl" | "en"` (optional, default from config)
- Response `200`:
```json
{ "text": "Cześć, to jest test.", "language": "pl", "duration_s": 3.2, "processing_s": 1.1 }
```
- Errors: `400` (missing/invalid audio), `413` (file too large, limit 50 MB), `503` (model not ready), `500` (unexpected).

Implementation notes:
- Write the upload to a temp file, transcribe, always delete it in `finally`.
- Use `vad_filter=True` in faster-whisper to skip silence and reduce hallucinated text on quiet clips.
- Return an empty `text` with a friendly message in the UI (not an error) when nothing was detected.
- Run the blocking transcription in a threadpool (`run_in_threadpool`) so the server stays responsive.

## 9. Milestones (build in this order, commit after each)

1. **Scaffold** — repo structure, `pyproject.toml`, ruff config, `.gitignore`, `.env.example`, README stub.
2. **Transcriber core** — `transcriber.py` that takes a file path + language and returns text; manual test with the two fixture files.
3. **API** — `/api/health` and `/api/transcribe` with tests (use a tiny model or mock in CI-style tests).
4. **UI** — record/stop, language dropdown, notepad, copy/clear, status + errors.
5. **Polish** — localStorage persistence, append/replace setting, error messages, README with setup + troubleshooting.
6. **Verification** — run the acceptance checklist below and fix what fails.

## 10. Acceptance Criteria (MVP is done when…)

- [ ] `uv sync && uv run uvicorn app.main:app` starts the app; opening `http://127.0.0.1:8000` shows the UI.
- [ ] First run downloads the model; subsequent runs work with the network disabled.
- [ ] Speaking a short English sentence yields correct text in the notepad.
- [ ] Speaking a short Polish sentence (with diacritics: ą ć ę ł ń ó ś ź ż) yields correct text **with diacritics preserved**.
- [ ] Mixed-language dictation works acceptably with Auto-detect; forcing PL or EN works as expected.
- [ ] Multiple recordings append into the notepad; Copy all puts the full text on the clipboard.
- [ ] Refreshing the page keeps the notepad content.
- [ ] Denying mic permission shows a clear message, no crash.
- [ ] Server only listens on `127.0.0.1`.
- [ ] `pytest` and `ruff check` pass.
- [ ] README lets a fresh clone get running in under 5 minutes.

## 11. README Must Include

- What it is, in two sentences.
- Prerequisites (Python version, `uv`, optional CUDA notes, ffmpeg only if actually needed).
- Install + run commands.
- Config table (env vars above).
- Model size vs. speed/quality guidance.
- Privacy statement (what is and isn't sent anywhere).
- Troubleshooting: mic blocked, slow transcription, wrong language detected, CUDA not found.

## 12. Roadmap (post-MVP, do NOT build now)

1. **Push-to-talk global hotkey** (e.g. hold a key anywhere → record → release → transcribe).
2. **Paste into the active window** automatically (clipboard + simulated paste), so it works like a real dictation tool.
3. **Pseudo-streaming:** transcribe in chunks while still recording, using VAD to cut on pauses.
4. **Transcript history:** local SQLite, searchable, exportable as `.md`/`.txt`.
5. **Text clean-up pass:** punctuation/capitalization fixes, filler-word removal, optionally via a small local LLM.
6. **Custom vocabulary:** prompt hints for names/jargon (`initial_prompt` in Whisper).
7. **Desktop wrapper** (Tauri/Electron or system-tray app) instead of a browser tab.
8. **Voice commands** ("new line", "delete that", "comma").

## 13. Conventions for Claude Code

- Keep it small and readable; prefer the standard library and FastAPI built-ins.
- Type hints on all Python functions; docstrings only where intent isn't obvious.
- One responsibility per module; no premature abstractions or plugin systems.
- Commit messages in imperative mood (`Add transcribe endpoint`). One logical change per commit.
- Never commit `.env`, model files, or recorded audio (beyond the tiny test fixtures).
- Before declaring a milestone done, actually run the app/tests and report what you verified.
- If a requirement can't be met as written, stop and explain the trade-off rather than silently changing scope.
