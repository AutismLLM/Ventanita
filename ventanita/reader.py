"""reader.py — "what does it say?" Click the chat, capture the window, OCR it."""
import time
import mss
import pyautogui
import pytesseract
from PIL import Image


def last_messages(window_region, chat_list_row):
    """Click the chat with the badge, scroll to bottom, OCR the visible region."""
    cx, cy, cw, ch = chat_list_row
    pyautogui.click(cx + cw // 2, cy + ch // 2)
    time.sleep(0.5)

    pyautogui.scroll(-10)
    time.sleep(0.3)

    x, y, w, h = window_region
    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    return pytesseract.image_to_string(img, lang="spa+eng")
