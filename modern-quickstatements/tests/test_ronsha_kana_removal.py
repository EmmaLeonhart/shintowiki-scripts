"""Guard for the P460 branch of generate_kana_qualifier_remove (2026-09-10).

A Shikinai Ronsha holds the Engishiki entry's katakana reading as a top-level
P1814, while the ojp-hani P1448 official name lives on the entry item it points
at with P460. The removal of the ronsha's copy is confirmed against that entry.

The confirmation must be an EXACT value match. Three of the fifteen 論社 in this
population point at an entry that carries a DIFFERENT entry's reading — their own
reading belongs to a 同社坐 sub-entry that has no item of its own, so P460 lands on
the parent shrine instead:

    Q135040970 -アメワカヒコノ  ->  Q135040959 阿須伎神社   アスキノ
    Q135041051 -イタテ-        ->  Q135041050 曽枳能夜神社  ソキノヤノ
    Q135199795 シロカネ-       ->  Q135041546 銀山上神社   カナヤマノヘノ

A STRENDS("カミノヤシロ")-style check — which is what the same generator's
same-item branch uses, correctly, because there the name and the reading are on
one statement — would read all three as confirmed and delete a reading that
exists nowhere else on Wikidata.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_kana_qualifier_remove as g  # noqa: E402

SUFFIX = g.SUFFIX


@pytest.mark.parametrize("top", ["アナサハノ-", "モロヲカ-", "-カラクニイタテノ", "-オホクタマ"])
def test_exact_match_confirms(top):
    assert g.ronsha_removal_confirmed(top, top + SUFFIX)


@pytest.mark.parametrize("top,done", [
    ("-アメワカヒコノ", "アスキノ" + SUFFIX),        # Q135040970 -> 阿須伎神社
    ("-イタテ-", "ソキノヤノ" + SUFFIX),             # Q135041051 -> 曽枳能夜神社
    ("シロカネ-", "カナヤマノヘノ" + SUFFIX),         # Q135199795 -> 銀山上神社
])
def test_a_different_entrys_reading_never_confirms(top, done):
    """These three are the whole reason the check is exact rather than STRENDS."""
    assert not g.ronsha_removal_confirmed(top, done)


def test_unsuffixed_qualifier_never_confirms():
    """The relocation is not done until the カミノヤシロ form is there."""
    assert not g.ronsha_removal_confirmed("アナサハノ-", "アナサハノ-")


def test_hiragana_top_level_is_never_removed():
    """The modern reading is not this pipeline's business, and removing it would
    take the only reading a reader can actually use."""
    assert not g.ronsha_removal_confirmed("あなざわてんじんしゃ", "あなざわてんじんしゃ" + SUFFIX)


def test_query_does_not_concat_in_sparql():
    """The exact-value comparison lives in Python on purpose: expressing it as
    FILTER(STR(?done) = CONCAT(STR(?top), "カミノヤシロ")) made Blazegraph return
    504 Gateway Timeout on 2026-09-10."""
    src = open(g.__file__, encoding="utf-8").read()
    ronsha_block = src.split("ronsha_q = f", 1)[1].split('"""', 2)[1]
    assert "CONCAT" not in ronsha_block
