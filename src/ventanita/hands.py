"""hands.py — "type like a human." Kill switch aborts mid-message, no exceptions."""
import random
import time
import threading

import pyautogui
import keyboard

_kill_flag = threading.Event()


def _on_killswitch():
    _kill_flag.set()


def arm_killswitch(key="f9"):
    _kill_flag.clear()
    keyboard.add_hotkey(key, _on_killswitch)


def type_and_send(text, input_pos, think_delay, type_jitter):
    time.sleep(random.uniform(*think_delay))
    if _kill_flag.is_set():
        return False

    pyautogui.click(*input_pos)

    for ch in text:
        if _kill_flag.is_set():
            return False
        pyautogui.write(ch)
        time.sleep(random.uniform(*type_jitter))

    if _kill_flag.is_set():
        return False

    pyautogui.press("enter")
    return True
