"""main.py — the loop. unread badge on a row -> click chat -> read text -> think -> type reply -> rescan -> loop."""
import logging
import logging.handlers
import os
import random
import time
from datetime import datetime

import yaml
from dotenv import load_dotenv

from . import db, reader, parser, brain, gate, hands

CONFIG_PATH = "config.yaml"

log = logging.getLogger("ventanita")


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def in_active_hours(active_hours):
    hour = datetime.now().hour
    return active_hours[0] <= hour < active_hours[1]


def run():
    load_dotenv(override=True)
    config = load_config()
    log.setLevel(logging.INFO)
    # Rotate at midnight, keep a week of history -- logs shouldn't grow forever.
    handler = logging.handlers.TimedRotatingFileHandler(
        config["paths"]["log"], when="midnight", backupCount=7
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)

    conn = db.connect(config["paths"]["db"])
    db.seed_menu_from_file(conn, config["paths"]["menu"])
    hands.arm_killswitch(config["safety"]["killswitch_key"])

    timing = config["timing"]

    log.info("=" * 50)
    log.info("Ventanita (RE)STARTED -- pid=%s", os.getpid())
    log.info("=" * 50)
    if not (config["window"].get("unread_badge_x_range") and config["window"].get("list_scan_range")):
        # The 0.1 fixed-row fallback is gone on purpose (it misfired into the
        # wrong chat, see CHANGELOG 0.2); without the scan band there is nothing to do.
        log.error("window.unread_badge_x_range / list_scan_range missing -- run calibrate.py; nothing will be answered")
    print("Ventanita running. Kill switch: %s" % config["safety"]["killswitch_key"])

    while True:
        if not in_active_hours(timing["active_hours"]):
            time.sleep(60)
            continue

        replied = drain_unread(conn, config)

        # One human-plausible pause after a batch, not one per chat: inside
        # the drain each reply already carries its own think_delay plus real
        # typing time, so 4 people get answered in a minute or three. Stacking
        # a 10-60s post_send_pause between each of them on top of that would
        # turn a burst into a 5+ minute queue, which reads less human, not more.
        if replied:
            time.sleep(random.uniform(*timing["post_send_pause"]))

        time.sleep(timing["check_interval_sec"])


def drain_unread(conn, config):
    """Answer every unread, allowed chat visible right now, up to
    safety.max_chats_per_drain. Returns how many replies were actually sent.

    Rescans the chat list from scratch after every single chat we open:
    opening/closing a chat and our own sent reply both reorder the list, so
    a y-coordinate found before a click can point at a different chat after
    it. No coordinate ever survives across a click.
    """
    win = config["window"]
    max_chats = config["safety"].get("max_chats_per_drain", 4)
    if not (win.get("unread_badge_x_range") and win.get("list_scan_range")):
        return 0

    opened = replied = 0
    while opened < max_chats:
        # Once the kill switch is down, every send is refused until restart.
        # Opening more chats would just mark them read with no reply.
        if hands.killed():
            log.warning("Kill switch is down; not opening any more chats")
            break
        found = _next_allowed_row(config)
        if found is None:
            break
        opened += 1
        if _handle_chat(conn, config, *found):
            replied += 1

    if opened >= max_chats:
        log.info("Drain cap hit (%d chats); anything still unread waits for next cycle", max_chats)
    return replied


def _next_allowed_row(config):
    """Topmost unread row that passes the allowlist, as (row_y, row_label),
    or None if nothing unread is allowed.

    Disallowed rows are skipped and the scan keeps going down the list --
    an allowed chat sitting below a disallowed one must still get its turn.
    Disallowed rows stay unread forever (we never open them), so they get
    re-OCR'd and re-skipped on every rescan; that's a cheap single-row OCR.
    """
    win = config["window"]
    rows = reader.find_unread_rows(
        win["unread_badge_x_range"], win["list_scan_range"], win["chat_list_row"][3]
    )
    allowed_chats = config["safety"].get("allowed_chats")
    for row_y in rows:
        row_label = reader.read_row_label(win["chat_list_row"], row_y)
        if gate.chat_allowed(row_label, allowed_chats):
            return row_y, row_label
        log.info("Skipped unread chat not in allowlist: %r", row_label.strip()[:80])
    return None


def _handle_chat(conn, config, row_y, row_label):
    """Open the unread row at row_y, reply if it deserves one, close it.
    Returns True if a reply was actually sent."""
    win = config["window"]
    timing = config["timing"]

    # The row label was OCR'd BEFORE any click (while row_y was fresh) and
    # is the chat's identity: OCR never gives us a phone number, so the
    # display name is the key (see parser.identity_from_label for caveats).
    name, key = parser.identity_from_label(row_label)

    raw = reader.last_messages(win["region"], win["chat_list_row"], row_y=row_y)

    # Don't answer mid-sentence. If the row still says "typing..." wait a
    # little (bounded) and then re-read the chat so the reply is to the
    # finished thought, not to the snapshot taken while they were composing.
    if _wait_while_typing(win, row_y, timing.get("typing_wait_sec", 15)):
        raw = reader.last_messages(win["region"], win["chat_list_row"], row_y=row_y)

    msg = parser.clean(raw, number=key, name=name)

    if not msg.text:
        log.info("Nothing readable in chat %s, closing without reply", key)
        hands.close_chat()
        return False

    # Dedup: if the latest inbound line is exactly what we last answered for
    # this chat, this is a re-read of the same screen, not a new message.
    # Don't burn an LLM call and don't send the same reply twice.
    if msg.text == db.last_user_message(conn, key):
        log.info("Already answered latest line from %s, skipping: %r", key, msg.text[:80])
        hands.close_chat()
        return False

    history = db.recent_orders(conn, key)
    notes, message_history = _remember(
        conn, key, name, config["llm"], timing.get("session_gap_hours", 3)
    )
    menu = db.active_menu(conn)
    db.add_message(conn, key, "user", msg.text)

    reply_text = brain.reply(
        msg.text, history, menu, config["llm"], msg.recent_context, message_history, notes
    )
    ok, reason = gate.should_send(reply_text, msg, config)

    # reader.last_messages() already opened this chat to read it.
    # Leaving it open makes WhatsApp Web stop marking this customer's
    # NEXT messages as unread, so the badge scan would never see them --
    # confirmed live: a customer's follow-ups sat unanswered because the
    # chat stayed open after we replied. So close it before returning,
    # in every case except a kill-switch abort (a human is likely
    # intervening manually then; don't fight them for window focus).
    sent = False
    if ok:
        sent = hands.type_and_send(
            reply_text,
            win["input_pos"],
            timing["think_delay"],
            timing["type_jitter"],
        )
        if sent:
            if msg.item:
                db.add_order(conn, key, f"{msg.qty} {msg.item} {msg.note}".strip())
            db.add_message(conn, key, "assistant", reply_text)
            log.info("Sent reply to %s: %s", key, reply_text)
        else:
            log.warning("Kill switch aborted send to %s", key)
    else:
        log.info("Flagged, not sent (%s): %s", reason, reply_text)

    killswitch_aborted = ok and not sent
    if not killswitch_aborted:
        hands.close_chat()
    return sent


def _remember(conn, key, name, llm_config, gap_hours):
    """What we know about this customer right now, as (notes, session_turns).

    Memory works like a person's: the CURRENT conversation is recalled turn
    by turn, older ones survive only as a short written note. A session ends
    when the customer goes quiet for gap_hours; the first message after that
    gap folds everything since the note was last written into a fresh note
    (one cheap LLM call, inline, no background job) and the raw replay
    starts over from empty.

    If that summary call fails the note is left alone and the unfolded turns
    are replayed raw as before -- a customer must never lose their reply to a
    bookkeeping error. The next boundary simply tries again with the same
    turns, since notes_ts only moves when a note is actually written.
    """
    _number, _name, _seen, notes, notes_ts = db.get_or_create_customer(conn, key, name)
    turns = db.messages_since(conn, key, notes_ts)
    last_ts = db.last_user_message_ts(conn, key)

    if turns and last_ts and db.hours_between(last_ts, db.now()) >= gap_hours:
        try:
            notes = brain.summarize_session(notes or "", turns, llm_config)
            db.update_customer_notes(conn, key, notes)
            log.info("Folded %d turns from %s into note: %s", len(turns), key, notes)
            turns = []
        except Exception as e:  # noqa: BLE001 -- any failure here must not cost the reply
            log.warning("Session summary failed for %s, replaying raw history: %s", key, e)
    return notes or "", turns


def _wait_while_typing(win, row_y, wait_cap_sec, poll_sec=3):
    """Poll the chat-list row while it shows "typing..."; returns True if it
    ever did, meaning the caller should re-read the chat before replying.

    Bounded by wait_cap_sec and then we answer whatever was last read rather
    than wait forever. Synchronous on purpose: this is a single-window bot
    and real concurrency would be far more machinery than the problem is
    worth. The honest cost is that a burst of chats can each add up to the
    cap on top of their own think/typing time; keep the cap short.
    """
    saw_typing = False
    deadline = time.monotonic() + wait_cap_sec
    while not hands.killed():
        label = reader.read_row_label(win["chat_list_row"], row_y)
        if not reader.is_typing(label):
            if saw_typing:
                log.info("Typing stopped, re-reading chat before replying")
            return saw_typing
        saw_typing = True
        if time.monotonic() >= deadline:
            log.info("Still typing after %ss, replying to what was read", wait_cap_sec)
            return True
        time.sleep(poll_sec)
    return saw_typing


if __name__ == "__main__":
    run()
