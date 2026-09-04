"""trigger.py — "did anything happen?" Dumb, fast, free. No VLM here."""
import mss
import pytesseract
from PIL import Image

_last_count = 0


def badge_changed(badge_corner):
    """Crop the unread-badge region, OCR the digit, compare to last seen value."""
    global _last_count
    x, y, w, h = badge_corner
    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    text = pytesseract.image_to_string(img, config="--psm 7 digits").strip()
    count = int(text) if text.isdigit() else 0

    changed = count != _last_count and count > 0
    _last_count = count
    return changed
