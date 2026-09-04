"""main.py — the loop. badge goes up -> click chat -> read text -> think -> type reply -> loop."""
import logging
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
    logging.basicConfig(
        filename=config["paths"]["log"],
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("ventanita")

    conn = db.connect(config["paths"]["db"])
    db.seed_menu_from_file(conn, config["paths"]["menu"])
    hands.arm_killswitch(config["safety"]["killswitch_key"])

    win = config["window"]
    timing = config["timing"]

    log.info("Ventanita started.")
    print("Ventanita running. Kill switch: %s" % config["safety"]["killswitch_key"])

    while True:
        if not in_active_hours(timing["active_hours"]):
            time.sleep(60)
            continue

        if trigger.badge_changed(win["badge_corner"]):
            raw = reader.last_messages(win["region"], win["chat_list_row"])
            msg = parser.clean(raw, number="self-chat", name="self")

            customer = db.get_or_create_customer(conn, msg.number, msg.name)
            history = db.recent_orders(conn, msg.number)
            menu = db.active_menu(conn)

            reply_text = brain.reply(msg.text, history, menu, config["llm"])
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
