"""reader.py — "what does it say?" Click the chat, capture the window, OCR it."""
import time
import mss
import pyautogui
import pytesseract
from PIL import Image

_BADGE_GREEN = (33, 192, 99)
_COLOR_TOLERANCE = 30


def find_unread_row_y(badge_x, scan_range):
    """Scan a 1px-wide column for WhatsApp's unread-badge green; return the
    topmost match's y, or None if no unread badge is visible right now."""
    top, bottom = scan_range
    with mss.mss() as sct:
        shot = sct.grab({"left": badge_x, "top": top, "width": 1, "height": bottom - top})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    for y in range(img.height):
        r, g, b = img.getpixel((0, y))
        if (
            abs(r - _BADGE_GREEN[0]) < _COLOR_TOLERANCE
            and abs(g - _BADGE_GREEN[1]) < _COLOR_TOLERANCE
            and abs(b - _BADGE_GREEN[2]) < _COLOR_TOLERANCE
        ):
            return top + y
    return None


def read_row_label(chat_list_row, row_y):
    """OCR just the row at row_y (name + timestamp + snippet) -- used to check
    an unread chat against an allowlist before ever opening or replying to it."""
    cx, _cy, cw, ch = chat_list_row
    top = row_y - ch // 2
    with mss.mss() as sct:
        shot = sct.grab({"left": cx, "top": top, "width": cw, "height": ch})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    return pytesseract.image_to_string(img, lang="spa+eng")


def last_messages(window_region, chat_list_row, row_y=None):
    """Click the chat row, scroll to bottom, OCR the visible message area.

    row_y overrides chat_list_row's fixed y (from find_unread_row_y) -- a
    fixed position can get hijacked by unrelated list reordering (e.g. the
    bot's own sent messages bumping a different chat back to the top).
    """
    cx, cy, cw, ch = chat_list_row
    if row_y is not None:
        cy = row_y - ch // 2

    pyautogui.click(cx + cw // 2, cy + ch // 2)
    time.sleep(0.5)

    pyautogui.scroll(-10)
    time.sleep(0.3)

    x, y, w, h = window_region
    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    return pytesseract.image_to_string(img, lang="spa+eng")
