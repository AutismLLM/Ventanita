"""db.py — "memory." One SQLite file, three tables, zero server."""
import sqlite3
from datetime import datetime, timezone

_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    number TEXT PRIMARY KEY,
    name TEXT,
    first_seen TEXT,
    notes TEXT
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
"""


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_or_create_customer(conn, number, name=""):
    row = conn.execute(
        "SELECT number, name, first_seen, notes FROM customers WHERE number = ?",
        (number,),
    ).fetchone()
    if row:
        return row
    conn.execute(
        "INSERT INTO customers (number, name, first_seen, notes) VALUES (?, ?, ?, ?)",
        (number, name, _now(), ""),
    )
    conn.commit()
    return (number, name, _now(), "")


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
