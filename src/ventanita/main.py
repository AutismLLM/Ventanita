"""main.py — the loop. badge goes up -> click chat -> read text -> think -> type reply -> loop."""
import logging
import logging.handlers
import os
import time
from datetime import datetime

import yaml
from dotenv import load_dotenv

from . import db, trigger, reader, parser, brain, gate, hands

CONFIG_PATH = "config.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def in_active_hours(active_hours):
    hour = datetime.now().hour
    return active_hours[0] <= hour < active_hours[1]


def run():
    load_dotenv(override=True)
    config = load_config()
    log = logging.getLogger("ventanita")
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

    win = config["window"]
    timing = config["timing"]

    log.info("=" * 50)
    log.info("Ventanita (RE)STARTED -- pid=%s", os.getpid())
    log.info("=" * 50)
    print("Ventanita running. Kill switch: %s" % config["safety"]["killswitch_key"])

    while True:
        if not in_active_hours(timing["active_hours"]):
            time.sleep(60)
            continue

        if trigger.badge_changed(win["badge_corner"]):
            row_y = None
            if win.get("unread_badge_x_range") and win.get("list_scan_range"):
                row_y = reader.find_unread_row_y(win["unread_badge_x_range"], win["list_scan_range"])

            allowed_chats = config["safety"].get("allowed_chats")
            if allowed_chats and row_y is not None:
                row_label = reader.read_row_label(win["chat_list_row"], row_y)
                if not any(name.lower() in row_label.lower() for name in allowed_chats):
                    log.info("Skipped unread chat not in allowlist: %r", row_label.strip()[:80])
                    time.sleep(timing["check_interval_sec"])
                    continue

            raw = reader.last_messages(win["region"], win["chat_list_row"], row_y=row_y)
            msg = parser.clean(raw, number="self-chat", name="self")

            customer = db.get_or_create_customer(conn, msg.number, msg.name)
            history = db.recent_orders(conn, msg.number)
            message_history = db.recent_messages(conn, msg.number)
            menu = db.active_menu(conn)
            db.add_message(conn, msg.number, "user", msg.text)

            reply_text = brain.reply(
                msg.text, history, menu, config["llm"], msg.recent_context, message_history
            )
            ok, reason = gate.should_send(reply_text, msg, config)

            if ok:
                sent = hands.type_and_send(
                    reply_text,
                    win["input_pos"],
                    timing["think_delay"],
                    timing["type_jitter"],
                )
                if sent:
                    if msg.item:
                        db.add_order(conn, msg.number, f"{msg.qty} {msg.item} {msg.note}".strip())
                    db.add_message(conn, msg.number, "assistant", reply_text)
                    log.info("Sent reply to %s: %s", msg.number, reply_text)
                else:
                    log.warning("Kill switch aborted send to %s", msg.number)
            else:
                log.info("Flagged, not sent (%s): %s", reason, reply_text)

            time.sleep(_jittered_pause(timing["post_send_pause"]))

        time.sleep(timing["check_interval_sec"])


def _jittered_pause(bounds):
    import random

    return random.uniform(*bounds)


if __name__ == "__main__":
    run()
