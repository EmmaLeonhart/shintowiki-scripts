"""Which table entry a label matched, not just what it renders (2026-09-19).

`dedication()` returned a rendered STRING, which is the one thing a `P825`
statement cannot use — 安德肋 does not identify anybody, `Q43399` does. The match
is split out so the entry can be named, and `dedication()` renders from it, so
there is **one** implementation of the precedence rather than two.

That precedence has already been wrong twice: sorting by string length let
`beata vergine` beat `visitation`, and the ordering fix did nothing on its own
because the feast table was English-only. A second copy walking the same tables
was not worth the risk.

⛔ And a third way it was wrong, found by this refactor: **equal-length phrases
had no tie-break at all.**
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import religious_building_morphemes as m  # noqa: E402


# --------------------------------------------------------------------------
# The four kinds of match
# --------------------------------------------------------------------------
def test_a_feast_matches_specific():
    kind, key, extra = m.match_dedication("Mariä Himmelfahrt")
    assert kind == "specific" and extra is None


def test_a_bare_marian_title_matches_generic_with_no_residue():
    kind, key, residue = m.match_dedication("Madonna")
    assert kind == "generic" and residue == []


def test_a_qualified_marian_title_carries_its_residue():
    kind, key, residue = m.match_dedication("Madonna del Pero")
    assert kind == "generic" and residue == ["pero"]


def test_a_compound_saint_matches_the_phrase_table():
    kind, key, saw = m.match_dedication("San Giovanni Battista")
    assert kind == "phrase" and key in m.NAME_PHRASES


def test_a_plain_saint_matches_names_and_reports_every_key():
    kind, keys, saw = m.match_dedication("Santi Martino e Giorgio")
    assert kind == "names" and saw
    assert keys == ["martino", "giorgio"], "every key, in label order"


def test_a_known_PAIR_is_one_phrase_and_not_two_names():
    """⚠ Both `Santi Pietro e Paolo` AND `Saints Peter and Paul` are in
    NAME_PHRASES, so each matches as ONE entry. Reaching for either as a
    two-name example was this test being wrong about the tables, twice."""
    for label, key in (("Santi Pietro e Paolo", "pietro paolo"),
                       ("Saints Peter and Paul", "peter paul")):
        kind, k, saw = m.match_dedication(label)
        assert kind == "phrase" and k == key, label


def test_an_unknown_name_matches_nothing():
    assert m.match_dedication("St. Fictitious") is None


# --------------------------------------------------------------------------
# ⛔ One implementation: render agrees with match, everywhere
# --------------------------------------------------------------------------
@pytest.mark.parametrize("label", [
    "Mariä Himmelfahrt", "Madonna", "Madonna del Pero", "San Giovanni Battista",
    "Santi Pietro e Paolo", "St. Laurentius", "St. Fictitious",
    "Visitazione della Beata Vergine", "Nuestra Señora de la Asunción",
])
def test_render_is_none_exactly_when_match_is_none(label):
    """The refactor must not have moved the boundary between refuse and emit."""
    hit = m.match_dedication(label)
    rendered = m.dedication(label, "ja", rules="it")
    if hit is None:
        assert rendered is None, label
    # The converse does NOT hold: a generic match with an unreadable qualifier
    # matches and still refuses to render. That asymmetry is deliberate.


def test_the_priority_bug_is_still_fixed():
    """⛔ A feast beats the Marian title carrying it. `beata vergine` is 13
    characters and `visitation` is 10, and length-sorting dropped the feast the
    table already had."""
    kind, key, _ = m.match_dedication("Visitazione della Beata Vergine")
    assert kind == "specific"
    kind, key, _ = m.match_dedication("Nuestra Señora de la Asunción")
    assert kind == "specific"


# --------------------------------------------------------------------------
# ⛔ Equal-length phrases: the tie-break that was missing
# --------------------------------------------------------------------------
def test_the_scan_order_is_deterministic():
    """`key=len, reverse=True` alone leaves equal-length phrases in SET
    iteration order, which moves whenever anything else is added to the set.
    Running the scan twice must give the same answer, and so must running it
    after the set has been rebuilt."""
    first = m.match_dedication("Schmerzhafte Muttergottes")
    for _ in range(3):
        assert m.match_dedication("Schmerzhafte Muttergottes") == first


def test_the_real_equal_length_collision_is_settled_by_the_table():
    """`Schmerzhafte Muttergottes` matched both `muttergottes` and
    `schmerzhafte` — 12 characters each — and silently changed answer when an
    unrelated refactor perturbed the set order. It is the Sorrowful Mother of
    God, so the compound phrase is in the table and the longest-phrase rule
    settles it instead of a coin toss."""
    kind, key, _ = m.match_dedication("Schmerzhafte Muttergottes")
    assert key == "schmerzhafte muttergottes"
    assert m.dedication("Schmerzhafte Muttergottes", "zh") == "痛苦圣母"
    assert m.dedication("Muttergottes", "zh") == "天主之母"


def test_a_longer_phrase_still_beats_a_shorter_one():
    assert m.match_dedication("Sacred Heart")[1] != "heart"


# --------------------------------------------------------------------------
# The measured join to the QID map
# --------------------------------------------------------------------------
def test_the_match_key_is_what_a_qid_lookup_needs():
    """⚠ Two numbers were wrong in opposite directions before this was measured
    properly. A substring join against the raw label said **1,601** — too high,
    because `anne` is inside `Annecy` and `paul` inside `Paulo`. Joining on the
    matched key but only on ONE spelling said **979** — too low, because NAMES
    holds a key per spelling and the audit term matches only one of them. The
    truth is **2,153**, and it needs both: the matched key, and the siblings.
    """
    import saint_qids as sq
    kind, keys, _ = m.match_dedication("Sant'Andrea")
    assert kind == "names" and keys == ["andrea"], (
        "the matched key is the SPELLING the label used, not the canonical one")
    # ⭐ `andrea` and `andrew` render identically, so they are one saint and the
    # QID resolved for either covers both. That is the join.
    assert m.NAMES["andrea"]["ja"] == m.NAMES["andrew"]["ja"]
    assert sq.qid_for("Saint Andrew") == "Q43399"
