"""The en-source and id-source rows come from ONE query, not two.

⛔ WHY THIS MATTERS, and why it is not a speed optimisation. The two original
queries differed only in which label they SELECT: both walked the same class set
and both carried the same per-language
`FILTER NOT EXISTS { rdfs:label ?x FILTER(LANG(?x) = lang) }`. So the expensive
part ran twice per language — 114 queries per run over 57 languages, each
returning ~37,000 rows. On 2026-09-21 this generator drew a 429 from WDQS at
language 18 of 57 while already using the shared transport, so pacing was not the
remaining lever. Asking fewer questions was. CLAUDE.md: *"You don't fucking
hammer it."*

⚠ Measured against the real endpoint on `shn` before shipping: en labels
identical (37,636/37,636), id labels identical (34,428/34,428), union of QIDs
identical, and a full single-language run produced output BYTE-IDENTICAL to the
committed file with 1 query instead of 2.

What these tests protect is the part a future edit could quietly break: the two
passes must keep receiving exactly what their own queries used to return, in the
same order, with English still winning an overlap.
"""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_multilang_quickstatements as g  # noqa: E402


def _b(qid, en=None, id_=None):
    row = {"item": {"value": "http://www.wikidata.org/entity/" + qid}}
    if en is not None:
        row["enLabel"] = {"value": en}
    if id_ is not None:
        row["idLabel"] = {"value": id_}
    return row


# Q1 en only. Q2 id only. Q3 both — English must win. Q4 has an en label that does
# NOT parse and an id label that does, which is the fall-through the two-pass shape
# exists for: the en pass must leave it unclaimed.
ROWS = [
    _b("Q1", en="Alpha Shrine"),
    _b("Q2", id_="Kuil Beta"),
    _b("Q3", en="Gamma Shrine", id_="Kuil Gamma"),
    _b("Q4", en="Some Random Building", id_="Kuil Delta"),
]


@pytest.fixture
def run(tmp_path, monkeypatch):
    """Run the generator for one language against ROWS, in a temp cwd."""
    calls = []

    def fake(query, label):
        calls.append(query)
        return list(ROWS)

    monkeypatch.setattr(g, "run_sparql", fake)
    monkeypatch.setattr(g, "ALL_LANGS", ["de"])
    monkeypatch.chdir(tmp_path)
    g.main()
    text = io.open(str(tmp_path / "quickstatements" / "de.txt"), encoding="utf-8").read()
    return calls, text


def test_one_query_per_language_not_two(run):
    calls, _ = run
    assert len(calls) == 1, "a language must cost ONE query; it used to cost two"


def test_the_one_query_asks_for_both_labels_and_drops_items_with_neither(run):
    calls, _ = run
    q = calls[0]
    assert '?enLabel' in q and '?idLabel' in q
    assert 'OPTIONAL' in q
    # The union the two original queries covered: an item with neither label was
    # in neither of them, so it must not appear now.
    assert 'FILTER(BOUND(?enLabel) || BOUND(?idLabel))' in q


def test_the_expensive_parts_are_still_there_exactly_once(run):
    """The saving must come from merging the SELECTs, never from loosening the
    class set or dropping the per-language existence filter — either would change
    which items are targeted."""
    q = run[0][0]
    assert q.count("wdt:P31/wdt:P279* wd:Q845945") == 1
    assert q.count("wdt:P31 wd:Q5393308") == 1
    assert q.count("FILTER NOT EXISTS") == 1
    assert 'FILTER(LANG(?existing) = "de")' in q
    assert "ORDER BY ?item" in q


def test_english_wins_an_overlap(run):
    _, text = run
    assert '# Source: EN "Gamma Shrine"' in text
    assert '# Source: ID "Kuil Gamma"' not in text


def test_an_unparseable_english_label_falls_through_to_the_id_pass(run):
    """Q4's en label does not parse. The en pass must NOT claim it — if it did,
    the item would be silently dropped instead of being read from Indonesian."""
    _, text = run
    assert '# Source: ID "Kuil Delta"' in text
    assert "Q4" in text


def test_every_row_that_can_yield_a_label_yields_one(run):
    _, text = run
    for qid in ("Q1", "Q2", "Q3", "Q4"):
        assert qid in text, qid


def test_the_two_replaced_queries_are_gone_from_the_call_path(run):
    """`make_sparql_en` and `make_sparql` may survive as references, but nothing
    in a run may issue them — that would put the second query back."""
    calls, _ = run
    for q in calls:
        assert not (q.count("rdfs:label ?enLabel") and "?idLabel" not in q)
        assert not (q.count("rdfs:label ?idLabel") and "?enLabel" not in q)
