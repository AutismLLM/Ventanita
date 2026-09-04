from ventanita import parser


def test_clean_strips_timestamps_and_system_lines():
    raw = "10:32 AM\nEnd-to-end encrypted\n2 al pastor sin cebolla"
    msg = parser.clean(raw, number="5219991234567", name="Juan")
    assert msg.text == "2 al pastor sin cebolla"
    assert msg.qty == 2
    assert msg.item == "al pastor"
    assert msg.note == "cebolla"


def test_clean_handles_plain_text_without_order_intent():
    msg = parser.clean("hola, tienen menu?")
    assert msg.qty == 0
    assert msg.item == ""


def test_identity_from_label_uses_name_line_minus_timestamp():
    name, key = parser.identity_from_label("Nico  10:32 PM\n2 al pastor sin cebolla")
    assert name == "Nico"
    assert key == "nico"


def test_identity_from_label_slug_is_stable_across_ocr_noise():
    _, a = parser.identity_from_label("Tía Lupe 9:01 am\nhola")
    _, b = parser.identity_from_label("  tía lupe\nqué onda")
    assert a == b == "t-a-lupe"


def test_identity_from_label_falls_back_to_unknown():
    assert parser.identity_from_label("") == ("unknown", "unknown")
    assert parser.identity_from_label("10:32 PM\n") == ("unknown", "unknown")
