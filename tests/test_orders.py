"""Order lifecycle, payment tracking, last-interaction lookups (0.2.4)."""
import sqlite3

import pytest

from ventanita import db


def _add_at(conn, customer, role, content, ts):
    conn.execute(
        "INSERT INTO messages (customer, role, content, ts) VALUES (?, ?, ?, ?)",
        (customer, role, content, ts),
    )
    conn.commit()


def test_open_order_is_the_newest_unfinished_one():
    conn = db.connect(":memory:")
    assert db.open_order(conn, "nico") is None

    first = db.add_order(conn, "nico", "2 al pastor")
    assert db.open_order(conn, "nico")[0] == first

    db.update_status(conn, first, "preparing")
    assert db.open_order(conn, "nico")[2] == "preparing"
    db.update_status(conn, first, "ready")
    assert db.open_order(conn, "nico")[2] == "ready"

    db.mark_paid(conn, first, "cash")
    assert db.open_order(conn, "nico") is None

    second = db.add_order(conn, "nico", "1 suadero")
    db.update_status(conn, second, "cancelled")
    assert db.open_order(conn, "nico") is None
    assert db.open_order(conn, "lupe") is None            # other customer untouched


def test_mark_paid_records_status_and_method():
    conn = db.connect(":memory:")
    order_id = db.add_order(conn, "nico", "2 al pastor")
    db.mark_paid(conn, order_id, "transfer")

    row = conn.execute(
        "SELECT status, payment_method FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    assert row == ("paid", "transfer")
    assert db.recent_orders(conn, "nico")[0][1] == "paid"


def test_last_payment_method_is_from_the_latest_paid_order():
    conn = db.connect(":memory:")
    assert db.last_payment_method(conn, "nico") is None

    a = db.add_order(conn, "nico", "2 al pastor")
    db.mark_paid(conn, a, "cash")
    b = db.add_order(conn, "nico", "3 suadero")
    db.mark_paid(conn, b, "mercado_pago")
    db.add_order(conn, "nico", "1 campechano")             # still open: not counted

    assert db.last_payment_method(conn, "nico") == "mercado_pago"


def test_preferred_payment_roundtrip():
    conn = db.connect(":memory:")
    db.get_or_create_customer(conn, "nico", "Nico")
    assert db.preferred_payment(conn, "nico") is None
    assert db.preferred_payment(conn, "nobody") is None

    db.set_preferred_payment(conn, "nico", "card")
    assert db.preferred_payment(conn, "nico") == "card"
    # The 0.2.3 tuple main.py unpacks is unchanged.
    assert len(db.get_or_create_customer(conn, "nico")) == 5


def test_unknown_status_or_method_is_rejected():
    conn = db.connect(":memory:")
    order_id = db.add_order(conn, "nico", "2 al pastor")
    with pytest.raises(ValueError):
        db.update_status(conn, order_id, "delivered")
    with pytest.raises(ValueError):
        db.mark_paid(conn, order_id, "bitcoin")
    with pytest.raises(ValueError):
        db.set_preferred_payment(conn, "nico", "iou")
    with pytest.raises(ValueError):
        db.add_order(conn, "nico", "1 suadero", status="pending")
    assert db.open_order(conn, "nico")[2] == "new"          # nothing slipped through


def test_last_interaction_counts_both_sides():
    conn = db.connect(":memory:")
    assert db.last_interaction_ts(conn, "nico") is None
    assert db.last_interactions(conn) == []

    _add_at(conn, "nico", "user", "hola", "2026-09-01T10:00:00+00:00")
    _add_at(conn, "nico", "assistant", "qué onda", "2026-09-01T10:00:05+00:00")
    _add_at(conn, "lupe", "user", "3 suadero", "2026-09-02T10:00:00+00:00")

    # Our own reply counts: "last heard from OR replied to".
    assert db.last_interaction_ts(conn, "nico") == "2026-09-01T10:00:05+00:00"
    assert db.last_interactions(conn) == [
        ("lupe", "2026-09-02T10:00:00+00:00"),
        ("nico", "2026-09-01T10:00:05+00:00"),
    ]


def test_connect_adds_payment_columns_to_a_pre_0_2_4_db(tmp_path):
    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE customers (number TEXT PRIMARY KEY, name TEXT, first_seen TEXT, notes TEXT, notes_ts TEXT)")
    old.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT, items TEXT, status TEXT, ts TEXT)")
    old.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT, role TEXT, content TEXT, ts TEXT)")
    old.execute("INSERT INTO customers VALUES ('nico', 'Nico', 't0', 'old note', 't1')")
    old.execute("INSERT INTO orders (customer, items, status, ts) VALUES ('nico', '2 al pastor', 'new', 't2')")
    old.execute("INSERT INTO messages (customer, role, content, ts) VALUES ('nico', 'user', 'hola', 't2')")
    old.commit()
    old.close()

    conn = db.connect(path)
    assert db.get_or_create_customer(conn, "nico") == ("nico", "Nico", "t0", "old note", "t1")
    assert db.preferred_payment(conn, "nico") is None
    assert db.open_order(conn, "nico") == (1, "2 al pastor", "new", "t2")
    assert db.last_interaction_ts(conn, "nico") == "t2"

    db.mark_paid(conn, 1, "cash")
    assert db.last_payment_method(conn, "nico") == "cash"
    # Opening again is a no-op, not a second ALTER.
    db.connect(path).close()
