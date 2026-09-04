from ventanita import gate


def test_empty_allowlist_allows_everything():
    assert gate.chat_allowed("Random Contact  10:32 PM\nhola", []) is True
    assert gate.chat_allowed("Random Contact", None) is True


def test_allowlist_is_case_insensitive_substring():
    assert gate.chat_allowed("NICO  10:32 PM\n2 al pastor", ["Nico"]) is True
    assert gate.chat_allowed("Comunidad Tacos\nnuevo aviso", ["Nico"]) is False


def test_pick_first_allowed_row_skips_disallowed_ones_above_it():
    # Same walk main._next_allowed_row does: disallowed rows are skipped,
    # not a reason to abandon the pass.
    rows = [(400, "Comunidad Tacos"), (490, "Mamá"), (580, "Nico  10:32 PM")]
    picked = next((y for y, label in rows if gate.chat_allowed(label, ["Nico"])), None)
    assert picked == 580
