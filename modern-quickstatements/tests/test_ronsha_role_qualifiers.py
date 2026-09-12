"""The ronsha role backfill must stay qualifier-only, and must keep its guard.

`generate_ronsha_role_qualifiers.py` attaches `P2868` to `P460` statements that
already exist. Two properties of it are load-bearing and neither is visible from
reading the output file casually.

**Qualifier-only.** Every line names the `P460` value it is attaching to, because
`direct_daily_edits.execute_line` finds the claim by value. That makes the line
look like a statement add, and it is not one — if a `-` ever appeared in front of
it, or the value column changed, the drip would remove or duplicate a disputed
identity rather than annotate it. The 2026-09-09 loss of four ojp-hani official
names came from exactly that shape.

**The guard.** `P31` is not exclusive. Items typed BOTH `Q135022904` (Ronsha) and
`Q135038714` (Disputed Shikinaisha) are Engishiki *entries* carrying the Ronsha
class, and `Q134917286` (Shikinaisha) is the same case;
`generate_ronsha_ojp_name_removals.py` documents this and excludes them. Measured
2026-09-12: the guard drops 10 items and 23 statements from a 469-item / 525-pair
population. A future edit that widens the SPARQL must not quietly re-include them.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

GENERATOR = os.path.join(MQ, "generate_ronsha_role_qualifiers.py")
OUTPUT = os.path.join(MQ, "ronsha_role_qualifiers.txt")

LINE = re.compile(r"^Q\d+\|P460\|Q\d+\|P2868\|Q135022904$")


def _source():
    with open(GENERATOR, encoding="utf-8") as fh:
        return fh.read()


def test_every_emitted_line_is_the_qualifier_only_shape():
    if not os.path.exists(OUTPUT):
        import pytest
        pytest.skip("output not generated in this checkout")
    with open(OUTPUT, encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]
    assert lines, "the file exists but is empty — that is a drained batch, not a bug, but check"
    bad = [ln for ln in lines if not LINE.match(ln)]
    assert not bad, f"{len(bad)} line(s) are not the expected shape, first: {bad[:1]}"


def test_the_batch_never_removes_anything():
    """A leading '-' would strip the whole P460 statement instead of annotating it."""
    if not os.path.exists(OUTPUT):
        import pytest
        pytest.skip("output not generated in this checkout")
    with open(OUTPUT, encoding="utf-8") as fh:
        assert not [ln for ln in fh if ln.startswith("-")]


def test_the_dual_typed_guard_is_still_in_the_RENDERED_query():
    """Checks the query the script actually sends, not its source text.

    An earlier version of this test accepted the QID appearing anywhere in the
    file, which a comment would have satisfied — and the QIDs only ever appear as
    constants, interpolated into the query, so a source-text check proves nothing
    about what gets sent.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("_gen_rrq", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    q = " ".join(mod.QUERY.split())
    for qid, what in (("Q134917286", "Shikinaisha"), ("Q135038714", "Disputed Shikinaisha")):
        assert f"FILTER NOT EXISTS {{ ?s wdt:P31 wd:{qid} }}" in q, (
            f"the {what} ({qid}) exclusion is not in the query being sent — P31 is "
            f"not exclusive and those items are Engishiki ENTRIES. Query was: {q}")
    assert "FILTER NOT EXISTS { ?st pq:P2868 ?any }" in q, (
        "the already-has-a-role exclusion is gone; this would overwrite the two "
        "Hiteisha statements")


def test_the_role_value_is_the_ronsha_class_itself():
    """Not a majority vote over the corpus: for an item typed Ronsha the role
    restates its own P31. If this ever becomes a different QID, the docstring's
    reasoning no longer holds and has to be rewritten with it."""
    assert 'RONSHA = "Q135022904"' in _source()


def test_the_statement_is_never_restated_with_a_reference_or_a_new_value():
    """The emitted line carries exactly one qualifier pair and nothing else — no
    S-prefixed reference, no second qualifier — so it cannot alter the claim."""
    src = _source()
    assert '"{s}|P460|{v}|P2868|{RONSHA}"' in src.replace("f\"", '"'), (
        "the emit shape changed; re-check that it is still qualifier-only")
