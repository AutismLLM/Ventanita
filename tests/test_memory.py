"""Session memory: 3h+ quiet = session over, old turns fold into a short note."""
import sqlite3

from ventanita import brain, db, main


def _add_at(conn, customer, role, content, ts):
    # add_message() always stamps "now"; tests need turns in the past.
    conn.execute(
        "INSERT INTO messages (customer, role, content, ts) VALUES (?, ?, ?, ?)",
        (customer, role, content, ts),
    )
    conn.commit()


def test_hours_between_iso_timestamps():
    assert db.hours_between("2026-09-04T10:00:00+00:00", "2026-09-04T13:30:00+00:00") == 3.5


def test_customer_row_carries_notes_and_notes_ts():
    conn = db.connect(":memory:")
    number, name, _seen, notes, notes_ts = db.get_or_create_customer(conn, "nico", "Nico")
    assert (number, name, notes, notes_ts) == ("nico", "Nico", "", None)

    db.update_customer_notes(conn, "nico", "Siempre pide al pastor sin cebolla.")
    _n, _name, _seen, notes, notes_ts = db.get_or_create_customer(conn, "nico")
    assert notes == "Siempre pide al pastor sin cebolla."
    assert notes_ts is not None


def test_connect_adds_notes_ts_to_a_pre_0_2_3_db(tmp_path):
    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE customers (number TEXT PRIMARY KEY, name TEXT, first_seen TEXT, notes TEXT)")
    old.execute("INSERT INTO customers VALUES ('nico', 'Nico', 't0', 'old note')")
    old.commit()
    old.close()

    conn = db.connect(path)
    assert db.get_or_create_customer(conn, "nico") == ("nico", "Nico", "t0", "old note", None)


def test_messages_since_only_returns_turns_after_the_note():
    conn = db.connect(":memory:")
    _add_at(conn, "nico", "user", "hola", "2026-09-01T10:00:00+00:00")
    _add_at(conn, "nico", "assistant", "qué onda", "2026-09-01T10:00:05+00:00")
    _add_at(conn, "nico", "user", "2 al pastor", "2026-09-02T10:00:00+00:00")

    assert len(db.messages_since(conn, "nico", None)) == 3
    assert db.messages_since(conn, "nico", "2026-09-01T12:00:00+00:00") == [("user", "2 al pastor")]
    assert db.messages_since(conn, "nico", "2026-09-03T00:00:00+00:00") == []


def test_last_user_message_ts_ignores_our_own_turns():
    conn = db.connect(":memory:")
    assert db.last_user_message_ts(conn, "nico") is None
    _add_at(conn, "nico", "user", "hola", "2026-09-01T10:00:00+00:00")
    _add_at(conn, "nico", "assistant", "qué onda", "2026-09-01T10:00:05+00:00")
    assert db.last_user_message_ts(conn, "nico") == "2026-09-01T10:00:00+00:00"


def test_remember_folds_old_session_into_note_after_gap(monkeypatch):
    conn = db.connect(":memory:")
    _add_at(conn, "nico", "user", "2 al pastor sin cebolla", "2026-01-01T10:00:00+00:00")
    _add_at(conn, "nico", "assistant", "van, al rato", "2026-01-01T10:00:10+00:00")

    calls = []

    def fake_summary(old_notes, turns, llm_config=None):
        calls.append((old_notes, turns))
        return "Nico: al pastor sin cebolla."

    monkeypatch.setattr(brain, "summarize_session", fake_summary)

    notes, turns = main._remember(conn, "nico", "Nico", {}, gap_hours=3)

    assert notes == "Nico: al pastor sin cebolla."
    assert turns == []                                   # session replay starts over
    assert calls == [("", [("user", "2 al pastor sin cebolla"), ("assistant", "van, al rato")])]
    assert db.get_or_create_customer(conn, "nico")[3] == "Nico: al pastor sin cebolla."


def test_remember_keeps_raw_turns_inside_a_session(monkeypatch):
    conn = db.connect(":memory:")
    db.add_message(conn, "nico", "user", "hola")       # just now: same session
    db.add_message(conn, "nico", "assistant", "qué onda")

    def boom(*_a, **_k):
        raise AssertionError("must not summarize mid-session")

    monkeypatch.setattr(brain, "summarize_session", boom)

    notes, turns = main._remember(conn, "nico", "Nico", {}, gap_hours=3)
    assert notes == ""
    assert turns == [("user", "hola"), ("assistant", "qué onda")]


def test_remember_accumulates_prior_note_and_only_new_turns(monkeypatch):
    conn = db.connect(":memory:")
    _add_at(conn, "nico", "user", "2 al pastor", "2026-01-01T10:00:00+00:00")
    db.get_or_create_customer(conn, "nico", "Nico")
    conn.execute(
        "UPDATE customers SET notes = ?, notes_ts = ? WHERE number = 'nico'",
        ("Le gusta el pastor.", "2026-01-01T14:00:00+00:00"),
    )
    _add_at(conn, "nico", "user", "hoy suadero, sin cilantro", "2026-01-02T10:00:00+00:00")
    _add_at(conn, "nico", "assistant", "sale", "2026-01-02T10:00:10+00:00")

    seen = {}

    def fake_summary(old_notes, turns, llm_config=None):
        seen["old_notes"], seen["turns"] = old_notes, turns
        return "Le gusta el pastor; a veces suadero sin cilantro."

    monkeypatch.setattr(brain, "summarize_session", fake_summary)
    notes, turns = main._remember(conn, "nico", "Nico", {}, gap_hours=3)

    assert seen["old_notes"] == "Le gusta el pastor."
    assert seen["turns"] == [("user", "hoy suadero, sin cilantro"), ("assistant", "sale")]  # not the already-folded turn
    assert notes == "Le gusta el pastor; a veces suadero sin cilantro."
    assert turns == []


def test_remember_survives_a_failed_summary(monkeypatch):
    conn = db.connect(":memory:")
    _add_at(conn, "nico", "user", "2 al pastor", "2026-01-01T10:00:00+00:00")

    def boom(*_a, **_k):
        raise RuntimeError("api down")

    monkeypatch.setattr(brain, "summarize_session", boom)
    notes, turns = main._remember(conn, "nico", "Nico", {}, gap_hours=3)

    assert notes == ""
    assert turns == [("user", "2 al pastor")]            # replayed raw, reply still happens
    assert db.get_or_create_customer(conn, "nico")[4] is None  # notes_ts untouched: retried next boundary


def test_clip_note_caps_at_a_sentence_end():
    long = "Pide pastor. " * 100
    clipped = brain.clip_note(long)
    assert len(clipped) <= brain.NOTE_MAX_CHARS
    assert clipped.endswith(".")
    assert brain.clip_note("corta.") == "corta."


def test_system_prompt_includes_note_only_when_present():
    with_note = brain._build_system_content([], [("Al pastor", 25.0)], notes="Siempre sin cebolla.")
    assert "Lo que recuerdas de este cliente" in with_note
    assert "Siempre sin cebolla." in with_note
    without = brain._build_system_content([], [("Al pastor", 25.0)], notes="  ")
    assert "Lo que recuerdas" not in without
