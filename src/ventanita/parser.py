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


_CONTEXT_LINES = 8
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def identity_from_label(row_label):
    """Turn an OCR'd chat-list row ("Nico  10:32 PM\nhola...") into
    (name, key) for the DB.

    OCR gives us a display name, never a phone number, so the name is the
    best stable-ish identity we have: `name` is the first non-empty line
    with any timestamp stripped, `key` is that lowercased/slugified so
    "Nico" and "nico " land on the same customers/orders/messages rows.
    Known limitation: two contacts with the same display name, or an OCR
    misread of the name, will share/split a record. Good enough for a
    taco stand; not worth a fuzzy-matching layer.
    """
    for line in row_label.splitlines():
        name = _TIMESTAMP_RE.sub("", line).strip()
        if name:
            key = _SLUG_RE.sub("-", name.lower()).strip("-")
            if key:
                return name, key
    return "unknown", "unknown"


@dataclass
class Message:
    number: str
    name: str
    text: str
    item: str = ""
    qty: int = 0
    note: str = ""
    recent_context: str = ""


def clean(raw_text, number="unknown", name="unknown"):
    """Strip timestamps/system noise, keep the latest inbound line, extract order intent."""
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    lines = [l for l in lines if not _SYSTEM_LINE_RE.search(l)]
    lines = [_TIMESTAMP_RE.sub("", l).strip() for l in lines]
    lines = [l for l in lines if l]

    latest = lines[-1] if lines else ""
    recent_context = "\n".join(lines[-_CONTEXT_LINES:])

    msg = Message(number=number, name=name, text=latest, recent_context=recent_context)

    match = _QTY_ITEM_RE.search(latest.lower())
    if match:
        msg.qty = int(match.group("qty"))
        msg.item = match.group("item").strip()
        msg.note = (match.group("note") or "").strip()

    return msg
