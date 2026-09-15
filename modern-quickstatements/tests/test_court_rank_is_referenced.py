"""Court rank must cite the article it was read from, and a bare statement must
stay reachable.

`audit_model_adoption.py`, 2026-09-15, measured P14005 at **2,026 referenced of
5,180 statements — 39%** — against 16,802/16,995 (98.9%) for P13723 and
6,172/6,379 (96.8%) for temple P825. It was the only property in the survey with
a citation gap of that size, and Emma had just named citations as one of the
three things in scope.

Two faults produced it, and either alone would have been survivable:

  1. The emitted line was a bare `QID|P14005|<rank>` with no reference at all,
     though the rank was read from a named ja.wikipedia article — the source was
     in hand and thrown away (the title was dropped when building `person_ranks`).
  2. The skip set was `existing_pairs()` — every pair that had the statement at
     all. So once a bare statement landed, the generator would never emit for it
     again, and nothing else could reference it either.

Together they are a ratchet: every run added unreferenced statements and made
them permanently unreachable. The fix is the `c121509e` shape — skip only what is
already REFERENCED, and re-emit an existing bare statement with the reference.

⚠ Re-emitting does not duplicate. QuickStatements matches the existing
(item, property, value) and attaches the reference to that statement.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(os.path.dirname(HERE), "generate_court_rank_quickstatements.py")


def _source():
    with open(GEN, encoding="utf-8") as fh:
        return fh.read()


def _emit_lines():
    """The `lines.append(...)` calls — the emit format, not the prose about it.

    Matching the docstring instead of the code is a mistake three tests in this
    repo made in two days.
    """
    return [l for l in _source().splitlines() if "lines.append(" in l]


def test_every_emitted_line_carries_the_reference():
    emits = _emit_lines()
    assert emits, "no lines.append found; the emit path moved and this test is blind"
    for line in emits:
        assert "S143|Q177837" in line and "S4656" in line, (
            f"court-rank line emitted without the jawiki reference: {line.strip()}")


def test_the_reference_is_the_canonical_shape():
    """Same S143/S4656 pair the saijin and honzon generators use, so the three
    populations carry one citation shape rather than three."""
    sib = os.path.join(os.path.dirname(HERE), "generate_saijin_quickstatements.py")
    with open(sib, encoding="utf-8") as fh:
        saijin = fh.read()
    assert 'S143|Q177837|S4656|"' in saijin, (
        "the sibling's reference shape changed; this test's premise is stale")
    assert 'S143|Q177837|S4656|"' in _source(), (
        "court rank uses a different reference shape from its siblings")


def test_the_skip_set_is_referenced_not_merely_existing():
    """The ratchet. Skipping on `have` is what made a bare statement permanent."""
    src = _source()
    assert "def referenced_pairs(" in src, (
        "referenced_pairs() is gone; the skip set is back to 'has the statement', "
        "which is the bug that produced 39% referenced")
    skip = re.search(r"if \(pq, rank_qid\) in (\w+):\s*\n\s*continue", src)
    assert skip, "could not find the skip guard in the emit loop"
    assert skip.group(1) == "referenced", (
        f"the emit loop skips on `{skip.group(1)}`, not `referenced` — an existing "
        "bare statement can never be given a reference")


def test_referenced_pairs_actually_asks_for_a_reference():
    """A query that forgets `prov:wasDerivedFrom` returns every pair and silently
    restores the old behaviour while looking correct."""
    src = _source()
    body = src[src.index("def referenced_pairs("):]
    body = body[: body.index("\ndef ")]
    assert "prov:wasDerivedFrom" in body, (
        "referenced_pairs() does not filter on a reference existing, so it returns "
        "every pair and skips everything")


def test_the_source_title_survives_to_the_emit():
    """The reference URL needs the ja.wikipedia title, which used to be discarded
    when person_ranks was built."""
    src = _source()
    assert "person_ranks.setdefault(pq, []).append((rank_qid, rank_name, title))" in src, (
        "the jawiki title is no longer carried into person_ranks; the reference "
        "URL has nothing to name")
    assert "ja.wikipedia.org/wiki/" in src and "urllib.parse.quote" in src, (
        "the reference URL is not built from the title, or is not percent-encoded")
