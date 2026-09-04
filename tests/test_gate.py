from ventanita import gate, parser

CONFIG = {
    "safety": {"max_reply_chars": 320, "confirm_above_mxn": 500},
    "timing": {"active_hours": [0, 24]},
}


def test_normal_reply_is_sent():
    msg = parser.clean("2 al pastor sin cebolla")
    ok, reason = gate.should_send("Claro, listo en 10 min. Total $50", msg, CONFIG)
    assert ok is True
    assert reason == "ok"


def test_high_value_order_is_flagged():
    msg = parser.clean("2 al pastor sin cebolla")
    ok, reason = gate.should_send("Gran pedido, total $999", msg, CONFIG)
    assert ok is False
    assert "exceeds" in reason


def test_outside_active_hours_is_flagged():
    config = {**CONFIG, "timing": {"active_hours": [8, 22]}}
    msg = parser.clean("2 al pastor sin cebolla")
    ok, reason = gate.should_send("Claro, total $50", msg, config, now_hour=3)
    assert ok is False
    assert reason == "outside active hours"
