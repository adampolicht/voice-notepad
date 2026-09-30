#!/bin/bash
# Build "Voice Notepad.app" into /Applications so it can be launched from the Dock
# with no visible Terminal. The app runs the local server in the foreground of its own
# process: it appears in the Dock while running, and right-click -> Quit stops the server.
# Re-run this any time to rebuild (e.g. if you move the project).

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Voice Notepad"
DEST="/Applications"
[ -w "$DEST" ] || DEST="$HOME/Applications"
mkdir -p "$DEST"
APP="$DEST/$APP_NAME.app"

echo "Building $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# --- Info.plist ---
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Voice Notepad</string>
  <key>CFBundleDisplayName</key><string>Voice Notepad</string>
  <key>CFBundleIdentifier</key><string>com.voicenotepad.app</string>
  <key>CFBundleExecutable</key><string>voice-notepad</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict>
</plist>
PLIST

# --- launcher executable (repo path baked in) ---
cat > "$APP/Contents/MacOS/voice-notepad" <<EOF
#!/bin/bash
REPO="$REPO"
EOF
cat >> "$APP/Contents/MacOS/voice-notepad" <<'EOF'
URL="http://127.0.0.1:8000"
open_browser() { open -a "Opera GX" "$URL" 2>/dev/null || open "$URL"; }

cd "$REPO" 2>/dev/null || { open_browser; exit 0; }

# Already running (this app, run.command, or a manual uvicorn)? Just open it.
if curl -s -m 2 "$URL/api/health" >/dev/null 2>&1; then open_browser; exit 0; fi

if [ ! -x "$REPO/.venv/bin/uvicorn" ]; then
  /usr/bin/osascript -e 'display alert "Voice Notepad" message "Dependencies are not installed yet. Open the project and run: uv sync"' >/dev/null 2>&1
  exit 1
fi

# Open the browser once the server reports healthy (model load can take a moment).
( for _ in $(seq 1 90); do
    curl -s -m 2 "$URL/api/health" | grep -q '"status"' && { open_browser; break; }
    sleep 1
  done ) &

# Run in the foreground so this app process IS the server: quitting the app stops it.
exec "$REPO/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000
EOF
chmod +x "$APP/Contents/MacOS/voice-notepad"

# --- icon: cream background + orange record circle (matches the UI) ---
TMP="$(mktemp -d)"
cat > "$TMP/icon.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024">
  <rect width="1024" height="1024" fill="#ece3d0"/>
  <rect x="140" y="150" width="744" height="150" fill="#211d15"/>
  <circle cx="512" cy="620" r="250" fill="#cf4f22"/>
</svg>
SVG
if qlmanage -t -s 1024 -o "$TMP" "$TMP/icon.svg" >/dev/null 2>&1 && [ -f "$TMP/icon.svg.png" ]; then
  ICONSET="$TMP/icon.iconset"; mkdir -p "$ICONSET"
  for s in 16 32 128 256 512; do
    sips -z $s $s      "$TMP/icon.svg.png" --out "$ICONSET/icon_${s}x${s}.png"      >/dev/null 2>&1
    sips -z $((s*2)) $((s*2)) "$TMP/icon.svg.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null 2>&1
  done
  iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/icon.icns" >/dev/null 2>&1 \
    && echo "Icon generated." || echo "Icon build skipped (iconutil failed)."
else
  echo "Icon build skipped (SVG render unavailable) — app will use the default icon."
fi
rm -rf "$TMP"

# Ad-hoc sign so Launch Services treats it as a stable app.
codesign --force --deep -s - "$APP" >/dev/null 2>&1 && echo "Ad-hoc signed." || true
# Refresh the icon/registration cache.
touch "$APP"

echo "Done: $APP"
open -R "$APP"
