# Voice Notepad

A personal, fully local dictation tool: speak into your mic and the transcribed text appears in an editable notepad you can copy elsewhere. Runs entirely on your machine (Polish + English), powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

> Full setup, config, and troubleshooting are filled in at the end of the build. This is a stub.

## Quick start
```bash
uv sync --extra dev
cp .env.example .env
uv run uvicorn app.main:app
# open http://127.0.0.1:8000
```
