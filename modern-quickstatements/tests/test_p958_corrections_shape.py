"""A P958 correction must never emit the shape that deletes the statement.

`generate_p958_corrections.py` used to emit `-Q|P13677|"id"|P958|"old"` for every
correction. That reads as "remove this qualifier" and is not: a '-' line matches on
entity+property+VALUE and wbremoveclaims takes the whole claim, its references and its
other qualifiers. It is the shape that cost four items their entire ojp-hani P1448 name
on 2026-09-09, and the reason `p958_corrections.txt` stayed unregistered for a month.

Two shapes replace it, and this pins which correction gets which:
  * section MISSING -> a plain add line, order-independent, safe in the atomic drip;
  * section WRONG   -> a remove-then-REBUILD pair for sequential_misc.txt, whose '-'
    line carries no qualifier fields and whose rebuild restores every other qualifier
    and every reference the live statement had.

And it pins the refusals: a statement this file cannot write back verbatim is reported,
not emitted with the unrenderable part silently dropped.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QS_DIR = os.path.dirname(HERE)
if QS_DIR not in sys.path:
    sys.path.insert(0, QS_DIR)

import direct_daily_edits as dde  # noqa: E402
import generate_p958_corrections as gen  # noqa: E402


def claim(value, sections=(), quals=None, refs=(), rank="normal"):
    c = {"mainsnak": {"snaktype": "value",
                      "datavalue": {"type": "string", "value": value}},
         "rank": rank, "qualifiers": {}, "references": list(refs)}
    if sections:
        c["qualifiers"]["P958"] = [
            {"snaktype": "value", "datavalue": {"type": "string", "value": s}}
            for s in sections]
    for prop, snaks in (quals or {}).items():
        c["qualifiers"][prop] = snaks
    return c


def entity_snak(qid):
    return {"snaktype": "value",
            "datavalue": {"type": "wikibase-entityid", "value": {"id": qid}}}


def run(table, claims):
    """build() over a fixed CORRECTIONS table and a fixed live-state map."""
    original = gen.CORRECTIONS
    gen.CORRECTIONS = table
    try:
        return gen.build(fetch=lambda qid: claims.get(qid, []))
    finally:
        gen.CORRECTIONS = original


def test_missing_section_is_a_plain_add_not_a_pair():
    adds, pairs, notes = run([("Q1", "181621", "1")],
                             {"Q1": [claim("181621")]})
    assert adds == ['Q1|P13677|"181621"|P958|"1"']
    assert pairs == []


def test_wrong_section_is_a_remove_then_rebuild_pair():
    live = claim("181329", sections=("1",),
                 quals={"P3831": [entity_snak("Q135159299")]})
    adds, pairs, notes = run([("Q2", "181329", "2")], {"Q2": [live]})
    assert adds == []
    assert pairs == ['-Q2|P13677|"181329"',
                     'Q2|P13677|"181329"|P958|"2"|P3831|Q135159299']


def test_the_removal_half_carries_no_qualifier_fields():
    """The refused shape has >3 pipe-separated fields; the real removal has exactly 3."""
    live = claim("181329", sections=("1",))
    _, pairs, _ = run([("Q2", "181329", "2")], {"Q2": [live]})
    removal = pairs[0]
    assert removal.startswith("-")
    assert len(removal.split("|")) == 3, removal
    parsed = dde.parse_qs_line(removal)
    assert parsed["is_removal"] and not parsed["qualifiers"] and not parsed["references"]
    # Reaching find_claim(None, ...) is how we know it was not refused, exactly as
    # tests/test_qualifier_removal_is_refused.py checks the legitimate removals.
    try:
        dde.execute_removal(None, None, parsed)
    except AttributeError:
        pass
    else:
        raise AssertionError("expected the call to reach find_claim(None, ...)")


def test_the_rebuild_restores_references():
    live = claim("181621", sections=("n/a",),
                 refs=[{"snaks-order": ["P248", "P13677"],
                        "snaks": {"P248": [entity_snak("Q135159299")],
                                  "P13677": [{"snaktype": "value",
                                              "datavalue": {"type": "string",
                                                            "value": "181621"}}]}}])
    _, pairs, _ = run([("Q3", "181621", "0")], {"Q3": [live]})
    assert pairs[1] == ('Q3|P13677|"181621"|P958|"0"|S248|Q135159299|S13677|"181621"')
    parsed = dde.parse_qs_line(pairs[1])
    assert parsed["references"] == [
        ("P248", {"type": "entity",
                  "value": {"entity-type": "item", "numeric-id": 135159299,
                            "id": "Q135159299"}}),
        ("P13677", {"type": "string", "value": "181621"}),
    ]


def test_a_correct_section_emits_nothing():
    adds, pairs, notes = run([("Q4", "181621", "n/a")],
                             {"Q4": [claim("181621", sections=("n/a",))]})
    assert adds == [] and pairs == []
    assert "already" in notes[0]


def test_a_non_normal_rank_is_reported_not_rebuilt():
    live = claim("181621", sections=("1",), rank="deprecated")
    adds, pairs, notes = run([("Q5", "181621", "2")], {"Q5": [live]})
    assert adds == [] and pairs == []
    assert "rank" in notes[0] and "NOT emitted" in notes[0]


def test_an_unrenderable_qualifier_is_reported_not_dropped():
    live = claim("181621", sections=("1",),
                 quals={"P1234": [{"snaktype": "value",
                                   "datavalue": {"type": "quantity",
                                                 "value": {"amount": "+3"}}}]})
    adds, pairs, notes = run([("Q6", "181621", "2")], {"Q6": [live]})
    assert adds == [] and pairs == []
    assert "cannot write back" in notes[0]


def test_two_statements_with_the_same_id_are_not_value_matched():
    """A value-matched removal cannot say which of two it takes."""
    adds, pairs, notes = run(
        [("Q7", "181621", "2")],
        {"Q7": [claim("181621", sections=("1",)), claim("181621", sections=("3",))]})
    assert adds == [] and pairs == []
    assert "cannot say which" in notes[0]


def test_the_staged_file_holds_only_add_lines():
    path = os.path.join(QS_DIR, "p958_corrections.txt")
    if not os.path.exists(path):
        return
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            assert not line.startswith("-"), line


def test_the_file_is_registered_in_the_drip():
    assert "p958_corrections.txt" in dde.ATOMIC_FILES
