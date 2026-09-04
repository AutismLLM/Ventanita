#!/usr/bin/env bash
# Opens WhatsApp Web in a real, visible browser window on this machine so
# calibrate.py / main.py (pyautogui, mss) can see and interact with it.
# Not part of the bot itself — a dev convenience for setup and testing.
set -euo pipefail

BROWSER_BIN="${VENTANITA_BROWSER_BIN:-brave-browser}"

if ! command -v "$BROWSER_BIN" >/dev/null 2>&1; then
    echo "Browser binary '$BROWSER_BIN' not found. Set VENTANITA_BROWSER_BIN to your browser's binary name." >&2
    exit 1
fi

echo "Opening WhatsApp Web in a new $BROWSER_BIN window..."
"$BROWSER_BIN" --new-window "https://web.whatsapp.com" >/dev/null 2>&1 &
disown

sleep 2
WIN_ID=$(wmctrl -l | grep -i "whatsapp" | head -1 | awk '{print $1}')
if [ -n "$WIN_ID" ]; then
    wmctrl -ia "$WIN_ID"
    echo "WhatsApp Web window found and raised: $WIN_ID"
else
    echo "Window not detected yet — it may still be loading. Check manually if calibrate.py can't find it."
fi
