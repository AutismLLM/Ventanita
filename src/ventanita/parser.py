"""parser.py — "make it clean." The error-shrinking layer. LLM only sees this output."""
import re
from dataclasses import dataclass

_TIMESTAMP_RE = re.compile(r"\b\d{1,2}:\d{2}\s?(?:AM|PM|am|pm)?\b")
_SYSTEM_LINE_RE = re.compile(
    r"(mensajes y llamadas|end-to-end encrypt|cifrados de extremo a extremo|"
    r"hoy|today|ayer|yesterday)",
    re.IGNORECASE,
)
_QTY_ITEM_RE = re.compile(
    r"(?P<qty>\d+)\s*(?P<item>[a-zA-ZáéíóúñÁÉÍÓÚÑ ]+?)"
    r"(?:\s+sin\s+(?P<note>[a-zA-ZáéíóúñÁÉÍÓÚÑ ]+))?$"
)


@dataclass
class Message:
    number: str
    name: str
    text: str
    item: str = ""
    qty: int = 0
    note: str = ""


def clean(raw_text, number="unknown", name="unknown"):
    """Strip timestamps/system noise, keep the latest inbound line, extract order intent."""
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    lines = [l for l in lines if not _SYSTEM_LINE_RE.search(l)]
    lines = [_TIMESTAMP_RE.sub("", l).strip() for l in lines]
    lines = [l for l in lines if l]

    latest = lines[-1] if lines else ""

    msg = Message(number=number, name=name, text=latest)

    match = _QTY_ITEM_RE.search(latest.lower())
    if match:
        msg.qty = int(match.group("qty"))
        msg.item = match.group("item").strip()
        msg.note = (match.group("note") or "").strip()

    return msg
