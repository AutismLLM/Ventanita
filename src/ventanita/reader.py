"""reader.py — "what does it say?" Find unread rows, click one, capture the window, OCR it."""
import time
import mss
import pytesseract
from PIL import Image

# pyautogui is imported inside the functions that click, not at the top:
# importing it needs a live X display, and the pure pixel-scan helpers
# below are meant to be unit-testable on a synthetic image without one.

_BADGE_GREEN = (33, 192, 99)
_COLOR_TOLERANCE = 30


def _is_badge_green(pixel):
    r, g, b = pixel
    return (
        abs(r - _BADGE_GREEN[0]) < _COLOR_TOLERANCE
        and abs(g - _BADGE_GREEN[1]) < _COLOR_TOLERANCE
        and abs(b - _BADGE_GREEN[2]) < _COLOR_TOLERANCE
    )


def badge_pixel_rows(img):
    """Every y (image-relative) that has at least one badge-green pixel."""
    hits = []
    for y in range(img.height):
        for x in range(img.width):
            if _is_badge_green(img.getpixel((x, y))):
                hits.append(y)
                break
    return hits


def cluster_rows(ys, row_height):
    """Collapse a sorted list of pixel hits into one y per chat row.

    A badge is a ~20px tall circle, so it lights up ~20 consecutive y values.
    Anything closer than one row-height to the previous hit is the same badge;
    a gap of a row-height or more means a new row. Returns the topmost y of
    each cluster, which is what the old single-row scan returned too.
    """
    rows = []
    for y in ys:
        if rows and y - rows[-1] < row_height:
            continue
        rows.append(y)
    return rows


def find_unread_rows(badge_x_range, scan_range, row_height):
    """Scan a small x-band down the chat list for WhatsApp's unread-badge
    green; return the y of EVERY badge found, topmost first ([] if none).

    A single exact x doesn't hold: WhatsApp shifts the badge left when a row
    shows its extra dropdown-chevron affordance (observed ~22px), so we scan
    a band instead of one pixel column. row_height (chat_list_row's height)
    is what stops one badge's ~20 rows of green pixels counting as 20 hits.
    """
    x_left, x_right = badge_x_range
    top, bottom = scan_range
    with mss.mss() as sct:
        shot = sct.grab(
            {"left": x_left, "top": top, "width": x_right - x_left, "height": bottom - top}
        )
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    return [top + y for y in cluster_rows(badge_pixel_rows(img), row_height)]


def find_unread_row_y(badge_x_range, scan_range, row_height=1):
    """Topmost unread row's y, or None. Thin wrapper kept for callers that
    only ever want one row."""
    rows = find_unread_rows(badge_x_range, scan_range, row_height)
    return rows[0] if rows else None


def read_row_label(chat_list_row, row_y):
    """OCR just the row at row_y (name + timestamp + snippet) -- used to check
    an unread chat against an allowlist, and as the chat's identity, before
    ever opening or replying to it."""
    cx, _cy, cw, ch = chat_list_row
    top = row_y - ch // 2
    with mss.mss() as sct:
        shot = sct.grab({"left": cx, "top": top, "width": cw, "height": ch})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    return pytesseract.image_to_string(img, lang="spa+eng")


def last_messages(window_region, chat_list_row, row_y=None):
    """Click the chat row, scroll to bottom, OCR the visible message area.

    row_y overrides chat_list_row's fixed y (from find_unread_rows) -- a
    fixed position can get hijacked by unrelated list reordering (e.g. the
    bot's own sent messages bumping a different chat back to the top).
    """
    import pyautogui

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
