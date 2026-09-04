"""db.py — "memory." One SQLite file, four tables, zero server."""
import sqlite3
from datetime import datetime, timezone

_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    number TEXT PRIMARY KEY,
    name TEXT,
    first_seen TEXT,
    notes TEXT,
    notes_ts TEXT,
    preferred_payment TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT,
    items TEXT,
    status TEXT,
    ts TEXT,
    payment_method TEXT
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
CREATE INDEX IF NOT EXISTS messages_customer_ts ON messages (customer, ts);
"""

# How an order moves at a taco stand: taken -> on the plancha -> on the
# counter -> settled. cancelled is the only other exit. Anything not in
# CLOSED_STATUSES is still "open" for this customer.
ORDER_STATUSES = ("new", "preparing", "ready", "paid", "cancelled")
CLOSED_STATUSES = ("paid", "cancelled")

# How the customer settled (or prefers to settle). Just labels the human
# records; no gateway is called. mercado_pago is here so today's manual
# "pagó por MP" entries keep the same name a real integration will use.
PAYMENT_METHODS = ("cash", "transfer", "card", "mercado_pago")


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    _migrate(conn)
    conn.commit()
    return conn


def _migrate(conn):
    """CREATE TABLE IF NOT EXISTS never adds a column to a table that already
    exists, so a live ventanita.db from an older version lacks the newer
    columns. Guarded ALTERs are the whole migration story; no versions table."""
    _add_column(conn, "customers", "notes_ts", "TEXT")            # 0.2.3
    _add_column(conn, "customers", "preferred_payment", "TEXT")   # 0.2.4
    _add_column(conn, "orders", "payment_method", "TEXT")         # 0.2.4


def _add_column(conn, table, column, decl):
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


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


def last_interaction_ts(conn, customer):
    """When we last heard from OR replied to this customer (ISO ts), or None.
    Derived from messages rather than stored on the customer row: the index
    on (customer, ts) makes MAX(ts) a single lookup, so a denormalized
    column would be a write on every message for nothing."""
    (ts,) = conn.execute(
        "SELECT MAX(ts) FROM messages WHERE customer = ?", (customer,)
    ).fetchone()
    return ts


def last_interactions(conn):
    """Every customer with a message, as (customer, last_ts), most recent
    first -- the one query a chat-list view needs."""
    return conn.execute(
        "SELECT customer, MAX(ts) AS last_ts FROM messages "
        "GROUP BY customer ORDER BY last_ts DESC"
    ).fetchall()


def recent_orders(conn, number, n=3):
    return conn.execute(
        "SELECT items, status, ts FROM orders WHERE customer = ? ORDER BY ts DESC LIMIT ?",
        (number, n),
    ).fetchall()


def open_order(conn, customer):
    """The customer's newest unfinished order as (id, items, status, ts),
    or None if everything is paid/cancelled. "Do they have something in
    flight right now" in one call."""
    marks = ", ".join("?" * len(CLOSED_STATUSES))
    return conn.execute(
        f"SELECT id, items, status, ts FROM orders "
        f"WHERE customer = ? AND status NOT IN ({marks}) "
        f"ORDER BY ts DESC, id DESC LIMIT 1",
        (customer, *CLOSED_STATUSES),
    ).fetchone()


def preferred_payment(conn, number):
    """How this customer likes to pay, or None if never recorded."""
    row = conn.execute(
        "SELECT preferred_payment FROM customers WHERE number = ?", (number,)
    ).fetchone()
    return row[0] if row else None


def set_preferred_payment(conn, number, method):
    _check(method, PAYMENT_METHODS, "payment method")
    conn.execute(
        "UPDATE customers SET preferred_payment = ? WHERE number = ?", (method, number)
    )
    conn.commit()


def last_payment_method(conn, customer):
    """Method used on this customer's most recently settled order, or None.
    Separate from preferred_payment: this is what actually happened last
    time, that is what they say they like."""
    row = conn.execute(
        "SELECT payment_method FROM orders WHERE customer = ? AND status = 'paid' "
        "ORDER BY ts DESC, id DESC LIMIT 1",
        (customer,),
    ).fetchone()
    return row[0] if row else None


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
    _check(status, ORDER_STATUSES, "order status")
    cur = conn.execute(
        "INSERT INTO orders (customer, items, status, ts) VALUES (?, ?, ?, ?)",
        (customer, items, status, _now()),
    )
    conn.commit()
    return cur.lastrowid


def update_status(conn, order_id, status):
    _check(status, ORDER_STATUSES, "order status")
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()


def mark_paid(conn, order_id, payment_method):
    """Settle an order: status -> paid and record how. This is the whole of
    payment tracking for now -- a human (or later the console) says which
    method was used; nothing here talks to a gateway."""
    _check(payment_method, PAYMENT_METHODS, "payment method")
    conn.execute(
        "UPDATE orders SET status = 'paid', payment_method = ? WHERE id = ?",
        (payment_method, order_id),
    )
    conn.commit()


def _check(value, allowed, what):
    if value not in allowed:
        raise ValueError(f"unknown {what} {value!r}; expected one of {allowed}")
