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
