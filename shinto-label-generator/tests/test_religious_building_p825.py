"""P825 from the dedication the label already names (2026-09-20).

Emma, 2026-09-18: *"using the dedicated to for other ontology not just labels"*.
The morpheme tables have resolved a label to a dedicatee since 2026-09-17, but
only ever to a STRING, and a string identifies nobody — 安德肋 is not a value a
statement can carry, `Q43399` is.

⛔ The guard that matters most here is the one that has nothing to catch yet:
`P825 → Q1188622` (重要文化財) asserts "dedicated to Important Cultural Property",
which asserts nothing. None of the current values is a designation — they are
saints, Marian titles, dogmas and feasts — and the check is made anyway, because
the day a designation enters the QID map is the day nobody is looking.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import religious_building_morphemes as m  # noqa: E402
import saint_qids as sq  # noqa: E402
import generate_religious_building_p825 as p825  # noqa: E402


@pytest.fixture(scope="module")
def emitted():
    pairs, stats = p825.rows()
    return pairs, stats


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------
def test_every_line_is_one_statement_per_item(emitted):
    pairs, _ = emitted
    assert pairs, "the corpus should produce statements"
    items = [q for q, _ in pairs]
    assert len(items) == len(set(items)), "one P825 line per item"
    for item, value in pairs:
        assert item.startswith("Q") and value.startswith("Q")


def test_the_values_are_all_validated(emitted):
    """⛔ Nothing is looked up at emit time. A dedicatee outside the checked map
    is refused, because the seed those maps grew from was 52% wrong."""
    pairs, _ = emitted
    known = set(sq.SAINT_QIDS.values()) | set(sq.QID_BY_RENDERING.values())
    for _, value in pairs:
        assert value in known, value


# --------------------------------------------------------------------------
# ⛔ The designation guard, which has nothing to catch and is made anyway
# --------------------------------------------------------------------------
def test_no_cultural_property_designation_is_ever_a_value(emitted):
    """CLAUDE.md states this for P825 outright: `P825 -> Q1188622` asserts
    "dedicated to Important Cultural Property", which asserts nothing."""
    pairs, _ = emitted
    for _, value in pairs:
        assert value not in p825.INVALID_VALUES, value


def test_the_guard_would_fire_if_one_appeared(monkeypatch):
    """A guard that has never fired is a guard nobody has tested."""
    monkeypatch.setitem(sq.QID_BY_RENDERING, "聖母", "Q1188622")
    sq._BY_RENDERING = None
    try:
        _pairs, stats = p825.rows()
        assert stats["⛔ cultural-property designation refused"] > 0
    finally:
        sq._BY_RENDERING = None


def test_the_designations_named_are_the_ones_claude_md_names():
    assert "Q1188622" in p825.INVALID_VALUES     # 重要文化財
    assert "Q1139795" in p825.INVALID_VALUES     # 国宝
    assert p825.INVALID_VALUE_ROOTS == {"Q858308"}


# --------------------------------------------------------------------------
# ⛔ Two dedicatees are two statements, so one is not emitted
# --------------------------------------------------------------------------
def test_a_two_saint_dedication_is_skipped_not_halved(emitted):
    """`Santi Martino e Giorgio` needs TWO statements; emitting one silently
    asserts the label names a single dedicatee."""
    _pairs, stats = emitted
    assert stats["two or more dedicatees"] > 0
    hit = m.match_dedication("Santi Martino e Giorgio")
    assert sq.qid_for_match(hit) is None


# --------------------------------------------------------------------------
# ⛔ Both QID maps are read
# --------------------------------------------------------------------------
def test_the_term_map_is_not_invisible():
    """`qid_for_match` read `QID_BY_RENDERING` alone at first, so the 48 terms in
    SAINT_QIDS — the whole first lookup — never reached the generator. It emitted
    2,168 statements from **14** distinct dedicatees where the measurement said
    4,155 from all of them. A map nothing reads is not a map."""
    assert len(sq._index()) > len(sq.QID_BY_RENDERING)
    # A term-map-only dedicatee, reachable only through the join.
    assert sq.qid_for_match(m.match_dedication("Sant'Andrea")) == "Q43399"


def test_the_concept_map_wins_where_they_overlap():
    """It is the later, script-validated lookup, and the overlaps were
    cross-checked when it was installed."""
    assert sq._index()["聖母被昇天"] == sq.QID_BY_RENDERING["聖母被昇天"]


def test_a_useful_number_of_dedicatees_are_reached(emitted):
    pairs, _ = emitted
    assert len(set(v for _, v in pairs)) > 30, (
        "43 distinct dedicatees when this was written; a collapse to a handful "
        "means one of the two maps has stopped being read")
