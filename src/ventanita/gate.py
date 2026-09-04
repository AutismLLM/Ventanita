"""gate.py — "should we really send this?" Returns (send: bool, reason: str)."""
from datetime import datetime


def should_send(reply_text, msg, config, now_hour=None):
    safety = config["safety"]
    active_hours = config["timing"]["active_hours"]

    hour = now_hour if now_hour is not None else datetime.now().hour
    if not (active_hours[0] <= hour < active_hours[1]):
        return False, "outside active hours"

    if len(reply_text) > safety["max_reply_chars"]:
        return False, f"reply too long ({len(reply_text)} chars)"

    if msg.qty and not msg.item:
        return False, "ambiguous parse: quantity without item"

    total_hint = _extract_total(reply_text)
    if total_hint is not None and total_hint > safety["confirm_above_mxn"]:
        return False, f"order total {total_hint} exceeds human-confirm threshold"

    return True, "ok"


def _extract_total(text):
    import re

    match = re.search(r"\$\s?(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None
