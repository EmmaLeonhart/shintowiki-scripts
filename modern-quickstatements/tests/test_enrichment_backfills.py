"""The enrichment backfills: adding to statements that already exist.

Emma, 2026-09-11, on generators that create but never enrich: *"the updating of
the existing ones to add more to them is kind of a very critical part that makes
it so that this work is productive."*

Three generators skipped any subject that already carried their property, so
their reference and qualifier bundles only ever landed on statements they
created. What is pinned here is the gate that makes each backfill honest — a
VALUE MATCH against what the source still says. Without it a citation asserts
something the source does not, which is worse than no citation.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import generate_address_citation_from_article as A  # noqa: E402


# ---- address normalisation --------------------------------------------------

@pytest.mark.parametrize("wikitext,stored", [
    # A wikilink keeps its display text: the same address written two ways.
    ("[[島根県]][[出雲市]]斐川町併川258", "島根県出雲市斐川町併川258"),
    ("[[群馬県|群馬県]]富岡市一ノ宮1535", "群馬県富岡市一ノ宮1535"),
    # A postal code is not part of the address.
    ("〒699-0621 島根県出雲市斐川町併川258", "島根県出雲市斐川町併川258"),
    # Whitespace of either width, and a <br>.
    ("島根県 出雲市　斐川町併川258", "島根県出雲市斐川町併川258"),
    ("島根県出雲市<br />斐川町併川258", "島根県出雲市斐川町併川258"),
    # A reference in the field is not part of the address.
    ("島根県出雲市斐川町併川258<ref>出典</ref>", "島根県出雲市斐川町併川258"),
    # Full-width digits: the two sources disagree about them freely.
    ("島根県出雲市斐川町併川２５８", "島根県出雲市斐川町併川258"),
])
def test_the_same_address_written_two_ways_matches(wikitext, stored):
    assert A.normalise(wikitext) == A.normalise(stored)


@pytest.mark.parametrize("a,b", [
    # Every one of these was REFUSED against live data on 2026-09-11, correctly.
    ("群馬県富岡市一ノ宮1535", "群馬県富岡市一ノ宮"),          # block number dropped
    ("兵庫県南あわじ市賀集鍛冶屋87-1", "兵庫県南あわじ市賀集鍛治屋87−1"),  # 冶 vs 治
    ("京都府京都市左京区大原来迎院町540", "京都市左京区大原来迎院町540"),   # prefecture dropped
    ("三重県鈴鹿市国府町1609", "三重県鈴鹿市三宅町"),           # a different town
    ("福井県坂井市三国町山王6-2-80", "福井県坂井市三国町山王6丁目2-80"),  # 丁目 written out
])
def test_a_different_address_does_not_match(a, b):
    """Normalisation must not be so eager that two real addresses collide. It
    strips markup and formatting, never an address component."""
    assert A.normalise(a) != A.normalise(b)


def test_only_a_matching_address_is_cited():
    by_title = {"X神社": [("Q1", "島根県出雲市斐川町併川258"),
                          ("Q2", "島根県出雲市斐川町神庭485")]}
    fields = {"X神社": "[[島根県]]出雲市斐川町併川258"}
    lines, verdicts = A.build_lines(by_title, fields)
    assert len(lines) == 1 and lines[0].startswith("Q1|P6375|")
    assert verdicts["article states a different address"] == 1


def test_the_line_carries_the_article_it_cites():
    by_title = {"X神社": [("Q1", "島根県出雲市斐川町併川258")]}
    lines, _v = A.build_lines(by_title, {"X神社": "島根県出雲市斐川町併川258"})
    assert lines == ['Q1|P6375|ja:"島根県出雲市斐川町併川258"'
                     '|S143|Q177837|S4656|"https://ja.wikipedia.org/wiki/X%E7%A5%9E%E7%A4%BE"']


def test_an_article_with_no_address_field_cites_nothing():
    by_title = {"X神社": [("Q1", "島根県出雲市斐川町併川258")]}
    lines, verdicts = A.build_lines(by_title, {})
    assert lines == []
    assert verdicts["article has no 所在地 field"] == 1


# ---- every backfill is reference/qualifier-only ------------------------------

BACKFILLS = ["address_citation_from_article.txt", "souken_p571_citations.txt",
             "saijin_named_as.txt"]


@pytest.mark.parametrize("name", BACKFILLS)
def test_a_backfill_never_removes_anything(name):
    """These attach to a statement that already exists. A '-' line would remove
    the whole statement instead, which is the shape that destroyed four ojp-hani
    official names on 2026-09-09."""
    path = os.path.join(MQ, name)
    if not os.path.exists(path):
        pytest.skip(f"{name} not generated here")
    for line in open(path, encoding="utf-8"):
        assert not line.startswith("-"), line


@pytest.mark.parametrize("name", BACKFILLS)
def test_a_backfill_is_registered_on_the_only_road_to_wikidata(name):
    """A generated file that no submitter lists is a file whose lines never flow
    — the drift this repo already had to fix once for the temple label files."""
    import direct_daily_edits as d
    assert name in d.ATOMIC_FILES
