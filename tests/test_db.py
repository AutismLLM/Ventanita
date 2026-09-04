from ventanita import db


def test_seed_menu_and_order_roundtrip(tmp_path):
    menu_file = tmp_path / "menu.txt"
    menu_file.write_text("Al pastor,25\nSuadero,25\n")

    conn = db.connect(":memory:")
    db.seed_menu_from_file(conn, str(menu_file))
    assert db.active_menu(conn) == [("Al pastor", 25.0), ("Suadero", 25.0)]

    db.get_or_create_customer(conn, "5219991234567", "Juan")
    order_id = db.add_order(conn, "5219991234567", "2 al pastor sin cebolla")
    assert order_id == 1

    recent = db.recent_orders(conn, "5219991234567")
    assert recent[0][0] == "2 al pastor sin cebolla"
    assert recent[0][1] == "new"


def test_seed_menu_is_idempotent(tmp_path):
    menu_file = tmp_path / "menu.txt"
    menu_file.write_text("Al pastor,25\n")

    conn = db.connect(":memory:")
    db.seed_menu_from_file(conn, str(menu_file))
    db.seed_menu_from_file(conn, str(menu_file))
    assert len(db.active_menu(conn)) == 1


def test_message_history_roundtrip_is_oldest_first():
    conn = db.connect(":memory:")
    db.add_message(conn, "5219991234567", "user", "hola")
    db.add_message(conn, "5219991234567", "assistant", "qué onda")
    db.add_message(conn, "5219991234567", "user", "2 al pastor")

    turns = db.recent_messages(conn, "5219991234567")
    assert turns == [
        ("user", "hola"),
        ("assistant", "qué onda"),
        ("user", "2 al pastor"),
    ]


def test_recent_messages_respects_limit():
    conn = db.connect(":memory:")
    for i in range(5):
        db.add_message(conn, "123", "user", f"msg{i}")

    turns = db.recent_messages(conn, "123", n=2)
    assert [content for _role, content in turns] == ["msg3", "msg4"]
