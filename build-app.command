#!/bin/bash
# Build "Voice Notepad.app" into /Applications as a tiny native Cocoa app (compiled with swiftc).
# Being a real GUI app, it finishes launching cleanly: a steady Dock icon (no endless bouncing),
# and Cmd-Q / right-click -> Quit works. It starts the server via scripts/serve.sh, passing its
# own PID, so quitting the app (any way, incl. Force Quit) stops the server within ~2s.
# Re-run this any time to rebuild (e.g. if you move the project).

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Voice Notepad"
DEST="/Applications"
[ -w "$DEST" ] || DEST="$HOME/Applications"
mkdir -p "$DEST"
APP="$DEST/$APP_NAME.app"
TMP="$(mktemp -d)"

echo "Building $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# --- Swift source (repo path baked in) ---
cat > "$TMP/main.swift" <<EOF
import Cocoa

let repoPath = "$REPO"
EOF
cat >> "$TMP/main.swift" <<'SWIFT'

// Port comes from .env (PORT) via `python -m app --print-port`; 8000 if that fails.
let urlString: String = {
    let p = Process()
    p.launchPath = "\(repoPath)/.venv/bin/python"
    p.arguments = ["-m", "app", "--print-port"]
    p.currentDirectoryPath = repoPath
    let out = Pipe(); p.standardOutput = out; p.standardError = Pipe()
    var port = "8000"
    if (try? p.run()) != nil {
        p.waitUntilExit()
        let s = String(decoding: out.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        if p.terminationStatus == 0, Int(s) != nil { port = s }
    }
    return "http://127.0.0.1:\(port)"
}()

final class AppDelegate: NSObject, NSApplicationDelegate {

    func applicationDidFinishLaunching(_ note: Notification) {
        if serverIsUp() {
            openBrowser()
        } else if startServer() {
            waitThenOpen()
        }
    }

    func serverIsUp() -> Bool {
        let p = Process()
        p.launchPath = "/usr/bin/curl"
        p.arguments = ["-s", "-m", "2", "\(urlString)/api/health"]
        let out = Pipe(); p.standardOutput = out; p.standardError = Pipe()
        do { try p.run() } catch { return false }
        p.waitUntilExit()
        let data = out.fileHandleForReading.readDataToEndOfFile()
        return p.terminationStatus == 0 && !data.isEmpty
    }

    // Launch the server via the watchdog, passing our own PID so it stops when we quit.
    func startServer() -> Bool {
        let python = "\(repoPath)/.venv/bin/python"
        if !FileManager.default.isExecutableFile(atPath: python) {
            alert("Dependencies are not installed yet.\nOpen the project folder and run:  uv sync")
            NSApp.terminate(nil); return false
        }
        let p = Process()
        p.launchPath = "/bin/bash"
        p.arguments = ["\(repoPath)/scripts/serve.sh", String(ProcessInfo.processInfo.processIdentifier)]
        do { try p.run() } catch {
            alert("Failed to start the server:\n\(error)"); NSApp.terminate(nil); return false
        }
        return true
    }

    func waitThenOpen() {
        DispatchQueue.global().async {
            for _ in 0..<90 {
                if self.serverIsUp() { break }
                Thread.sleep(forTimeInterval: 0.5)
            }
            DispatchQueue.main.async { self.openBrowser() }
        }
    }

    func openBrowser() {
        let p = Process()
        p.launchPath = "/usr/bin/open"
        p.arguments = [urlString]  // the user's default browser
        try? p.run()
    }

    // Clicking the Dock icon while running re-opens the tab.
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows: Bool) -> Bool {
        openBrowser(); return true
    }

    func alert(_ msg: String) {
        let a = NSAlert(); a.messageText = "Voice Notepad"; a.informativeText = msg
        a.alertStyle = .warning; a.runModal()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
SWIFT

swiftc -O "$TMP/main.swift" -o "$APP/Contents/MacOS/voicenotepad" -framework Cocoa
echo "Compiled native app."

# --- Info.plist ---
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Voice Notepad</string>
  <key>CFBundleDisplayName</key><string>Voice Notepad</string>
  <key>CFBundleIdentifier</key><string>com.voicenotepad.app</string>
  <key>CFBundleExecutable</key><string>voicenotepad</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>NSPrincipalClass</key><string>NSApplication</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict>
</plist>
PLIST

# --- icon: cream background + orange record circle (matches the UI) ---
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
    sips -z $s $s             "$TMP/icon.svg.png" --out "$ICONSET/icon_${s}x${s}.png"    >/dev/null 2>&1
    sips -z $((s*2)) $((s*2)) "$TMP/icon.svg.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null 2>&1
  done
  iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/icon.icns" >/dev/null 2>&1 \
    && echo "Icon generated." || echo "Icon build skipped (iconutil failed)."
else
  echo "Icon build skipped (SVG render unavailable) — app will use the default icon."
fi
rm -rf "$TMP"

codesign --force --deep -s - "$APP" >/dev/null 2>&1 && echo "Ad-hoc signed." || true
touch "$APP"

echo "Done: $APP"
open -R "$APP"
