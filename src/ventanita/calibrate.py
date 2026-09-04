"""calibrate.py — one-time setup helper. Click the corners, get a config.

Run this once with the WhatsApp window pinned, dark mode, zoom 100%.
Follow the prompts; it writes coordinates straight into config.yaml.
"""
import sys
import time

import pyautogui
import yaml

CONFIG_PATH = "config.yaml"
EXAMPLE_PATH = "config.example.yaml"


def _wait_click(prompt):
    input(f"{prompt}\nMove your mouse there, then press Enter...")
    return pyautogui.position()


def main():
    print("Ventanita calibration. You have 3 seconds after each Enter to hover; "
          "actually it reads the mouse position immediately on Enter, so hover first.")

    print("\n1) Hover the TOP-LEFT corner of the chat message area.")
    x1, y1 = _wait_click("Top-left of chat region")
    print("2) Hover the BOTTOM-RIGHT corner of the chat message area.")
    x2, y2 = _wait_click("Bottom-right of chat region")
    region = [min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)]

    print("\n3) Hover the TOP-LEFT of the small unread-badge digit.")
    bx1, by1 = _wait_click("Top-left of badge")
    print("4) Hover the BOTTOM-RIGHT of the small unread-badge digit.")
    bx2, by2 = _wait_click("Bottom-right of badge")
    badge_corner = [min(bx1, bx2), min(by1, by2), abs(bx2 - bx1), abs(by2 - by1)]

    print("\n5) Hover the message INPUT FIELD (where you type a reply).")
    ix, iy = _wait_click("Input field")
    input_pos = [ix, iy]

    print("\n6) Hover the TOP-LEFT of a chat row (fallback if no unread badge is found).")
    cx1, cy1 = _wait_click("Top-left of chat row")
    print("7) Hover the BOTTOM-RIGHT of that same chat row.")
    cx2, cy2 = _wait_click("Bottom-right of chat row")
    chat_list_row = [min(cx1, cx2), min(cy1, cy2), abs(cx2 - cx1), abs(cy2 - cy1)]

    print("\n8) Hover the LEFT edge of where the small green unread-count dot could "
          "appear on a chat row (it shifts ~20px when a row shows its dropdown chevron "
          "-- give it a generous band).")
    ux1, _uy1 = _wait_click("Left edge of unread-dot band")
    print("9) Hover the RIGHT edge of that same band.")
    ux2, _uy2 = _wait_click("Right edge of unread-dot band")
    unread_badge_x_range = [min(ux1, ux2), max(ux1, ux2)]

    print("\n10) Hover the TOP of the visible chat list (below the search bar).")
    _sx, sy_top = _wait_click("Top of chat list")
    print("11) Hover the BOTTOM of the visible chat list.")
    _sx2, sy_bottom = _wait_click("Bottom of chat list")
    list_scan_range = [min(sy_top, sy_bottom), max(sy_top, sy_bottom)]

    try:
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        with open(EXAMPLE_PATH) as f:
            config = yaml.safe_load(f)

    config["window"]["region"] = region
    config["window"]["badge_corner"] = badge_corner
    config["window"]["input_pos"] = input_pos
    config["window"]["chat_list_row"] = chat_list_row
    config["window"]["unread_badge_x_range"] = unread_badge_x_range
    config["window"]["list_scan_range"] = list_scan_range

    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)

    print(f"\nSaved to {CONFIG_PATH}. Do not move the WhatsApp window, or re-run this.")


if __name__ == "__main__":
    main()
