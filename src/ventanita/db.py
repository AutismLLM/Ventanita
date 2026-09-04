"""db.py — "memory." One SQLite file, three tables, zero server."""
import sqlite3
from datetime import datetime, timezone

_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    number TEXT PRIMARY KEY,
    name TEXT,
    first_seen TEXT,
    notes TEXT,
    notes_ts TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT,
    items TEXT,
    status TEXT,
    ts TEXT
);
CREATE TABLE IF NOT EXISTS menu (
    item TEXT,
    price REAL,
    available INTEGER
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT,
    role TEXT,
    content TEXT,
    ts TEXT
);
"""


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    _migrate(conn)
    conn.commit()
    return conn


def _migrate(conn):
    """CREATE TABLE IF NOT EXISTS never adds a column to a table that already
    exists, so a live ventanita.db from before 0.2.3 has no notes_ts. One
    guarded ALTER is the whole migration story; no versions table."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(customers)")}
    if "notes_ts" not in cols:
        conn.execute("ALTER TABLE customers ADD COLUMN notes_ts TEXT")


def _now():
    return datetime.now(timezone.utc).isoformat()


def now():
    """Current UTC timestamp in the same ISO form every row's ts uses."""
    return _now()


def hours_between(earlier_ts, later_ts):
    """Hours from one stored ISO timestamp to another."""
    a = datetime.fromisoformat(earlier_ts)
    b = datetime.fromisoformat(later_ts)
    return (b - a).total_seconds() / 3600


def get_or_create_customer(conn, number, name=""):
    """Returns (number, name, first_seen, notes, notes_ts). notes is the short
    "what you remember about this customer" text; notes_ts is when it was
    last rewritten (None if never), which is also where the current session's
    raw history starts -- everything before it is already folded into notes."""
    row = conn.execute(
        "SELECT number, name, first_seen, notes, notes_ts FROM customers WHERE number = ?",
        (number,),
    ).fetchone()
    if row:
        return row
    ts = _now()
    conn.execute(
        "INSERT INTO customers (number, name, first_seen, notes, notes_ts) VALUES (?, ?, ?, ?, NULL)",
        (number, name, ts, ""),
    )
    conn.commit()
    return (number, name, ts, "", None)


def update_customer_notes(conn, number, notes):
    """Replace the customer's memory note and stamp when it was written, so
    messages_since(notes_ts) is exactly the not-yet-summarized history."""
    conn.execute(
        "UPDATE customers SET notes = ?, notes_ts = ? WHERE number = ?",
        (notes, _now(), number),
    )
    conn.commit()


def add_message(conn, customer, role, content):
    conn.execute(
        "INSERT INTO messages (customer, role, content, ts) VALUES (?, ?, ?, ?)",
        (customer, role, content, _now()),
    )
    conn.commit()


def recent_messages(conn, customer, n=20):
    """Last n turns, oldest first -- ready to drop straight into an LLM messages array."""
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE customer = ? ORDER BY ts DESC LIMIT ?",
        (customer, n),
    ).fetchall()
    return list(reversed(rows))


def messages_since(conn, customer, since_ts=None, n=40):
    """Turns after since_ts (all of them if None), oldest first, capped to
    the last n. With since_ts = the customer's notes_ts this is "the current
    session": everything older already lives in the note."""
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE customer = ? AND ts > ? "
        "ORDER BY ts DESC, id DESC LIMIT ?",
        (customer, since_ts or "", n),
    ).fetchall()
    return list(reversed(rows))


def last_user_message(conn, customer):
    """Content of this customer's most recent inbound line, or None.
    Used to skip re-answering a chat when OCR re-reads the same text."""
    row = _last_user_row(conn, customer)
    return row[0] if row else None


def last_user_message_ts(conn, customer):
    """When this customer last wrote to us (ISO ts), or None. The gap from
    here to now is what decides whether a new message starts a new session."""
    row = _last_user_row(conn, customer)
    return row[1] if row else None


def _last_user_row(conn, customer):
    return conn.execute(
        "SELECT content, ts FROM messages WHERE customer = ? AND role = 'user' "
        "ORDER BY ts DESC, id DESC LIMIT 1",
        (customer,),
    ).fetchone()


def recent_orders(conn, number, n=3):
    return conn.execute(
        "SELECT items, status, ts FROM orders WHERE customer = ? ORDER BY ts DESC LIMIT ?",
        (number, n),
    ).fetchall()


def active_menu(conn):
    return conn.execute(
        "SELECT item, price FROM menu WHERE available = 1"
    ).fetchall()


def seed_menu_from_file(conn, menu_path):
    """Load menu.txt (item,price per line) into the menu table if it's empty."""
    (count,) = conn.execute("SELECT COUNT(*) FROM menu").fetchone()
    if count > 0:
        return

    with open(menu_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            item, price = line.rsplit(",", 1)
            conn.execute(
                "INSERT INTO menu (item, price, available) VALUES (?, ?, 1)",
                (item.strip(), float(price)),
            )
    conn.commit()


def add_order(conn, customer, items, status="new"):
    cur = conn.execute(
        "INSERT INTO orders (customer, items, status, ts) VALUES (?, ?, ?, ?)",
        (customer, items, status, _now()),
    )
    conn.commit()
    return cur.lastrowid


def update_status(conn, order_id, status):
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
