#!/usr/bin/env bash
# Starts a virtual X display (Xvfb) and opens WhatsApp Web inside it, so the
# bot's mouse/keyboard automation (pyautogui) runs there instead of on your
# real desktop (:0). Your actual mouse/keyboard are never touched.
#
# Usage: ./scripts/start_isolated_display.sh
# Then run the bot itself with DISPLAY set to the printed value, e.g.:
#   DISPLAY=:99 ventanita-calibrate
#   DISPLAY=:99 ventanita
set -euo pipefail

VDISPLAY="${VENTANITA_VDISPLAY:-:99}"
RES="${VENTANITA_VRES:-1920x1080x24}"
BROWSER_BIN="${VENTANITA_BROWSER_BIN:-brave-browser}"

if ! pgrep -f "Xvfb $VDISPLAY" >/dev/null 2>&1; then
    echo "Starting Xvfb on $VDISPLAY ($RES)..."
    Xvfb "$VDISPLAY" -screen 0 "$RES" >/tmp/ventanita_xvfb.log 2>&1 &
    disown
    sleep 1
else
    echo "Xvfb already running on $VDISPLAY."
fi

echo "Opening WhatsApp Web inside $VDISPLAY..."
DISPLAY="$VDISPLAY" "$BROWSER_BIN" --new-window --start-maximized "https://web.whatsapp.com" >/tmp/ventanita_browser.log 2>&1 &
disown

sleep 3
echo ""
echo "Isolated display ready: $VDISPLAY"
echo "Peek at it any time (does not touch your real screen or mouse):"
echo "  DISPLAY=$VDISPLAY scrot -o /tmp/ventanita_peek.png"
echo ""
echo "Run the bot against it:"
echo "  DISPLAY=$VDISPLAY ventanita-calibrate"
echo "  DISPLAY=$VDISPLAY ventanita"
