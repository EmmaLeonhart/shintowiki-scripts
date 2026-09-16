"""A bare temple P825 must stay reachable: the skip set is REFERENCED, not existing.

The shrine half of the same property was fixed on 2026-09-15, where the fault cost
10,514 unreachable statements. Temple P825 is in far better shape — 6,173 of 6,380
referenced on 2026-09-15, because we built nearly all of it ourselves from the
jawiki 本尊 field with the citation attached — so this closes a ratchet rather than
recovering a population. The 207 bare ones become reachable, and future runs stop
locking in their own.

⚠ Re-emitting does not duplicate. QuickStatements matches the existing
(item, property, value) and attaches the reference to that statement.

⚠ The skip branch still sets `pending`, and that is load-bearing, not leftover.
A form (秘仏, 仏像) qualifies the deity most recently seen in the same field, so a
pair that is skipped for being cited must still be available for a later form to
attach to — via the qualifier-only line. Dropping `pending` there would silently
lose the form on every already-cited honzon, which is most of them.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(os.path.dirname(HERE), "generate_honzon_quickstatements.py")


def _source():
    with open(GEN, encoding="utf-8") as fh:
        return fh.read()


def test_the_skip_set_is_referenced_not_merely_existing():
    src = _source()
    assert "def referenced_pairs(" in src, (
        "referenced_pairs() is gone; the skip set is back to 'has the statement', "
        "and a bare honzon can never be given its citation")
    skip = re.search(r"if \(qid, d\) in (\w+):\s*\n", src)
    assert skip, "could not find the skip guard in emit_for_temple"
    assert skip.group(1) == "referenced", (
        f"the emit loop skips on `{skip.group(1)}`, not `referenced`")


def test_referenced_pairs_actually_asks_for_a_reference():
    """A query that forgets `prov:wasDerivedFrom` returns every pair and silently
    restores the old behaviour while looking correct."""
    src = _source()
    body = src[src.index("def referenced_pairs("):]
    body = body[: body.index("\ndef ")] if "\ndef " in body else body
    assert "prov:wasDerivedFrom" in body, (
        "referenced_pairs() does not filter on a reference existing")
    assert "p:P825" in body and "ps:P825" in body, (
        "`wdt:P825` is the truthy shortcut and carries no reference node — a query "
        "written against it comes back empty, which reads as 'nothing is "
        "referenced' and re-emits everything")


def test_the_skipped_pair_is_still_available_to_a_later_form():
    """秘仏 attaches to the deity most recently seen in the field. A cited honzon is
    skipped for emit but must stay `pending`, or the form is dropped on exactly the
    temples whose honzon already landed — which is nearly all of them."""
    src = _source()
    branch = src[src.index("if (qid, d) in referenced:"):]
    branch = branch[: branch.index("continue")]
    assert "pending = (d, None)" in branch, (
        "the skip branch no longer records the extant statement, so a form later "
        "in the same 本尊 field has nothing to qualify and is counted as orphaned")


def test_the_emitted_line_still_carries_the_reference():
    emits = [l for l in _source().splitlines()
             if "lines.append(" in l and "P825" in l and "FORM_QUALIFIER" not in l]
    assert emits, "no value-emitting lines.append found; this test is blind"
    for line in emits:
        assert "P825" in line
    tail = [l for l in _source().splitlines() if "S143|Q177837|S4656" in l]
    assert tail, "the jawiki reference tail is gone from the emit"
