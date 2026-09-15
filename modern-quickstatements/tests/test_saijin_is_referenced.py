"""A bare shrine P825 must stay reachable: the skip set is REFERENCED, not existing.

`audit_model_adoption.py`, 2026-09-15, measured shrine P825 at **5,630 referenced
of 16,137 statements — 35%**. The temple half of the same property, built by
`generate_honzon_quickstatements.py` with the same S143/S4656 shape, sits at
6,172/6,379 (96.8%), and P13723 at 16,802/16,995 (98.9%).

The difference is not the emit — this generator has always cited the ja.wikipedia
article it read the deity from. It is the skip set. The shrine population is
largely older imports by other editors that landed bare, and skipping every pair
that merely *had* the statement meant this generator would never touch one again.
It is the only thing that knows which article named the deity, so ~10,500
statements were unreachable for good.

Same fault the second half of `generate_court_rank_quickstatements.py` had, fixed
the same way on the same day, and the `c121509e` shape before both.

⚠ Re-emitting does not duplicate. QuickStatements matches the existing
(item, property, value) and attaches the reference to that statement.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(os.path.dirname(HERE), "generate_saijin_quickstatements.py")


def _source():
    with open(GEN, encoding="utf-8") as fh:
        return fh.read()


def _emit_lines():
    """The `lines.append(...)` calls — the emit format, not the prose about it."""
    return [l for l in _source().splitlines() if "lines.append(" in l]


def test_every_emitted_line_carries_the_reference():
    emits = _emit_lines()
    assert emits, "no lines.append found; the emit path moved and this test is blind"
    for line in emits:
        assert "S143|Q177837" in line and "S4656" in line, (
            f"saijin line emitted without the jawiki reference: {line.strip()}")


def test_the_skip_set_is_referenced_not_merely_existing():
    """The ratchet. Skipping on `have` is what made a bare statement permanent."""
    src = _source()
    assert "def referenced_pairs(" in src, (
        "referenced_pairs() is gone; the skip set is back to 'has the statement', "
        "which is what left shrine P825 at 35% referenced")
    skip = re.search(r"if \(qid, d\) in (\w+):\s*\n\s*dup \+= 1", src)
    assert skip, "could not find the skip guard in the emit loop"
    assert skip.group(1) == "referenced", (
        f"the emit loop skips on `{skip.group(1)}`, not `referenced` — an existing "
        "bare statement can never be given a reference")


def test_referenced_pairs_actually_asks_for_a_reference():
    """A query that forgets `prov:wasDerivedFrom` returns every pair and silently
    restores the old behaviour while looking correct."""
    src = _source()
    body = src[src.index("def referenced_pairs("):]
    body = body[: body.index("\ndef ")] if "\ndef " in body else body
    assert "prov:wasDerivedFrom" in body, (
        "referenced_pairs() does not filter on a reference existing, so it returns "
        "every pair and skips everything")


def test_referenced_pairs_reads_statement_nodes_not_the_truthy_shortcut():
    """`wdt:P825` is the truthy shortcut and carries no reference node, so a query
    written against it can never see `prov:wasDerivedFrom` and would come back
    empty — which looks like "nothing is referenced" and re-emits all 16,000."""
    src = _source()
    body = src[src.index("def referenced_pairs("):]
    body = body[: body.index("\ndef ")] if "\ndef " in body else body
    assert "p:P825" in body and "ps:P825" in body, (
        "referenced_pairs() must go through the statement node (p:/ps:) to reach "
        "the reference")


def test_the_population_is_the_same_on_both_sides():
    """`have - referenced` is printed as the reachable count, so both queries have
    to select the same shrines. A P31 filter on one side only makes the number
    meaningless."""
    src = _source()
    both = [src[src.index(d):][: src[src.index(d):].index("\ndef ")]
            for d in ("def existing_pairs(", "def referenced_pairs(")]
    for body in both:
        assert "wdt:P31 wd:Q845945" in body, (
            "one side no longer restricts to Shinto shrines; the bare-count "
            "subtraction compares two different populations")
