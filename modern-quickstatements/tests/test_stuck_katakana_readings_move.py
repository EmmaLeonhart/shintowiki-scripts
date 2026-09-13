"""The top-level katakana reading gets MOVED onto the ojp-hani name, not stranded.

`generate_kana_qualifier_add.py` + `generate_kana_qualifier_remove.py` are already
a "move it, then delete" pair: the add puts `<reading>カミノヤシロ` on the item's
ojp-hani P1448 official name, and the remove retires the top-level P1814 once a
fresh SPARQL query confirms that exact value is there.

**The add half had a gate that excluded 742 readings from it.** Its second pass
was `SEED`, which only looked at names carrying NO P1814 qualifier at all
(`FILTER NOT EXISTS { ?st pq:P1814 ?anyq }`). A name that already held some other
reading was skipped, and the first pass (`APPEND`) only ever suffixes the
qualifier already sitting on a name — so for those items nothing moved the
top-level, and the remove step, which demands exactly `<top>カミノヤシロ`, had
nothing to confirm. Reported 2026-09-11 in `docs/stuck_katakana_readings.md`.

Emma ruled on 2026-09-13, given the choice between relocating those readings and
deleting them: *"Move it, then delete."* Widening the gate is that ruling.

What is pinned here is the shape of the ruling, in both directions:

* the add pass must NOT be gated on the name being qualifier-free, and
* the remove pass must KEEP its exact-value confirmation.

The second matters more than it looks. Widening the add puts a second and third
reading on names that already had one, and if the remove ever relaxed to "some
suffixed qualifier is present" it would start deleting top-level readings
confirmed by a DIFFERENT entry's reading — the exact loss
`ronsha_removal_confirmed` was written to prevent.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

ADD = os.path.join(MQ, "generate_kana_qualifier_add.py")
REMOVE = os.path.join(MQ, "generate_kana_qualifier_remove.py")
SUFFIX = "カミノヤシロ"


def _src(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _code(path):
    """Comment lines stripped. Both files quote the retired filter in prose to
    explain why it is retired, and asserting against that instead of the query is
    how two earlier tests in this repo went red against correct code."""
    return "\n".join(l for l in _src(path).splitlines()
                     if not l.lstrip().startswith("#"))


def test_the_move_pass_is_not_gated_on_the_name_being_empty():
    code = _code(ADD)
    assert "?anyq" not in code, (
        "the add pass is gated on the ojp-hani name having no P1814 qualifier "
        "again; that gate is what stranded 742 top-level katakana readings")
    move = code[code.index("move_q = f"):code.index("with open(ADD_FILE")]
    assert "?item p:P1814 ?ts . ?ts ps:P1814 ?top ." in move, (
        "the move pass no longer reads the item's top-level P1814 — there is "
        "nothing left to move")
    assert "OPTIONAL" in move and "?done" in move, (
        "without the OPTIONAL that reports the name's existing カミノヤシロ "
        "qualifiers, every run re-emits lines that already landed")


def test_the_move_pass_only_skips_a_reading_the_name_already_carries():
    """Idempotence, and nothing wider. The skip must test the exact value being
    added, not 'this name has some suffixed qualifier' — that broader test is the
    old gate wearing different clothes and would strand the same items."""
    code = _code(ADD)
    assert "if top + SUFFIX in done[(item, on)]:" in code, (
        "the already-present check is no longer an exact match on the value this "
        "pass would add")


def test_the_remove_pass_still_confirms_the_exact_value():
    """The other direction, and the one with teeth. Three of fifteen 論社 point at
    an entry whose ojp-hani name carries a DIFFERENT entry's reading; a
    STRENDS-style confirmation reads those as done and deletes a reading that
    exists nowhere else."""
    code = _code(REMOVE)
    assert "return is_katakana(top) and done == top + SUFFIX" in code, (
        "ronsha_removal_confirmed no longer requires the entry to carry THIS "
        "reading plus the suffix")
    assert "if top and top == base and is_katakana(top):" in code, (
        "the top-level removal no longer requires the confirmed qualifier to be "
        "exactly this reading plus the suffix")


def test_the_add_file_stays_add_only():
    """A '-' line here would remove the whole P1448 official name rather than a
    qualifier — the shape that destroyed four ojp-hani names on 2026-09-09."""
    path = os.path.join(MQ, "kana_qualifier_add.txt")
    if not os.path.exists(path):
        import pytest
        pytest.skip("not generated in this checkout")
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            assert not line.startswith("-"), f"{path}:{i} removes a statement: {line}"
            assert re.match(
                r'^Q\d+\|P1448\|ojp-hani:"[^"]+"\|P1814\|"[^"]+' + SUFFIX + r'"$', line), (
                f"{path}:{i} is not a カミノヤシロ qualifier add: {line}")


def test_a_gap_marked_reading_survives_the_move_intact():
    """The hyphen in these readings marks a portion the source did not read —
    `アハシマノ-イサハノ` for 粟島坐伊射波神社, the 坐 unread. It is part of the
    value, so the move must carry it across rather than strip or normalise it.
    Nothing in the add path touches the string except appending the suffix; this
    asserts the file agrees."""
    path = os.path.join(MQ, "kana_qualifier_add.txt")
    if not os.path.exists(path):
        import pytest
        pytest.skip("not generated in this checkout")
    hyphenated = [l.strip() for l in open(path, encoding="utf-8")
                  if re.search(r'\|P1814\|"[^"]*[-‐−][^"]*"', l)]
    assert hyphenated, (
        "no gap-marked reading is being moved at all — the widened pass reaches "
        "none of the population it was widened for")
    for line in hyphenated:
        value = line.rsplit('|"', 1)[1].rstrip('"')
        assert value.endswith(SUFFIX), line
        base = value[: -len(SUFFIX)]
        assert base, line
