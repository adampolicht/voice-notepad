#!/bin/bash
# Run the Voice Notepad server, and stop it automatically when the launching app exits.
# Usage: serve.sh [WATCH_PID]
#   WATCH_PID  optional; when that process disappears, the server is stopped.
# Used by the macOS app bundle so quitting the app (any way) always stops the server.

WATCH_PID="$1"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

# nohup on uvicorn itself so it survives even when the launching shell's process group
# is torn down (e.g. AppleScript's `do shell script` returning).
nohup "$REPO/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 >/dev/null 2>&1 &
SRV=$!

if [ -n "$WATCH_PID" ]; then
  while kill -0 "$WATCH_PID" 2>/dev/null; do sleep 2; done
  kill "$SRV" 2>/dev/null
fi

wait "$SRV" 2>/dev/null
