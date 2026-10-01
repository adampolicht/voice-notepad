#!/bin/bash
# Double-click this file to launch Voice Notepad.
# Starts the local server (if not already running) and opens it in the browser.
# Keep this Terminal window open while you use the app; close it (or press Ctrl+C) to stop.

cd "$(dirname "$0")" || exit 1

# Make sure dependencies are installed (first run only).
if [ ! -x ".venv/bin/uvicorn" ]; then
  echo "First run: installing dependencies with uv…"
  if command -v uv >/dev/null 2>&1; then uv sync; else
    echo "uv not found. Install it (brew install uv) and run this again."; exit 1
  fi
fi

# Port comes from .env (PORT), same as the server uses.
PORT="$(.venv/bin/python -m app --print-port 2>/dev/null || echo 8000)"
URL="http://127.0.0.1:$PORT"

open_browser() { open "$URL"; }

# Already running? Just open it.
if curl -s -m 2 "$URL/api/health" >/dev/null 2>&1; then
  echo "Voice Notepad is already running. Opening $URL"
  open_browser
  exit 0
fi

# Open the browser once the server reports healthy (model may take a moment to load).
(
  for _ in $(seq 1 90); do
    if curl -s -m 2 "$URL/api/health" | grep -q '"status"'; then open_browser; break; fi
    sleep 1
  done
) &

echo "Starting Voice Notepad on $URL — keep this window open. Press Ctrl+C to stop."
exec .venv/bin/python -m app
