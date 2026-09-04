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


def test_last_user_message_is_the_latest_inbound_line():
    conn = db.connect(":memory:")
    assert db.last_user_message(conn, "nico") is None

    db.add_message(conn, "nico", "user", "hola")
    db.add_message(conn, "nico", "assistant", "qué onda")
    db.add_message(conn, "nico", "user", "2 al pastor")
    db.add_message(conn, "nico", "assistant", "van")
    db.add_message(conn, "lupe", "user", "3 suadero")

    assert db.last_user_message(conn, "nico") == "2 al pastor"
    assert db.last_user_message(conn, "lupe") == "3 suadero"


def test_dedup_skips_identical_reread_but_not_new_text():
    # The check main._handle_chat makes before spending an LLM call.
    conn = db.connect(":memory:")
    db.add_message(conn, "nico", "user", "2 al pastor")
    assert "2 al pastor" == db.last_user_message(conn, "nico")       # re-read: skip
    assert "3 al pastor" != db.last_user_message(conn, "nico")       # new line: answer
    assert "2 al pastor" != db.last_user_message(conn, "lupe")       # other chat: answer
