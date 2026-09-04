"""hands.py — "type like a human." Kill switch aborts mid-message, no exceptions."""
import random
import subprocess
import time
import threading

import pyautogui
from pynput import keyboard

_kill_flag = threading.Event()
_listener = None


def arm_killswitch(key="f9"):
    global _listener
    _kill_flag.clear()
    target = getattr(keyboard.Key, key, None)

    def _on_press(pressed):
        if pressed == target:
            _kill_flag.set()

    _listener = keyboard.Listener(on_press=_on_press)
    _listener.daemon = True
    _listener.start()


def type_and_send(text, input_pos, think_delay, type_jitter):
    time.sleep(random.uniform(*think_delay))
    if _kill_flag.is_set():
        return False

    pyautogui.click(*input_pos)

    for ch in text:
        if _kill_flag.is_set():
            return False
        # pyautogui.write() silently drops/mangles non-ASCII chars (é, ñ, emoji) on X11.
        # xdotool type handles UTF-8 correctly via XTest.
        subprocess.run(["xdotool", "type", "--clearmodifiers", "--", ch], check=False)
        time.sleep(random.uniform(*type_jitter))

    if _kill_flag.is_set():
        return False

    pyautogui.press("enter")
    return True
