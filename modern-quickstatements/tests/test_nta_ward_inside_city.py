"""A ward is INSIDE the city Wikidata names — and a prefecture is not (2026-09-19).

Two results from the same measurement over the 15,948 targets the NTA matcher
could not place. One is a fix; the other is a refusal, and the refusal is the
more important half of this file because it looks exactly like the fix.

⭐ **The fix.** ``city_keys`` handled one direction — the registry writes 市+区 and
Wikidata labels the bare 区. The other was missing: Wikidata often carries the
designated CITY (京都市) while the registry files the corporation under city+ward
(京都市伏見区). Those do not conflict. 伏見区 is inside 京都市, so the registry is
simply more precise than the claim. 30 items where exactly one ward-level entry
sits inside the claimed city, 2 where several do but all read the same, 0 where
the readings differ.

⛔ **The refusal.** The obvious next widening is "unique within the PREFECTURE".
It looks like the national-uniqueness rule tightened by a prefecture the item
actually asserts. Measured: 3,379 candidates, and they are different temples.
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import generate_nta_kana as g  # noqa: E402

# One 京都市伏見区 entry, no bare-京都市 entry. The shape the fix exists for.
WARDS = {("京都市", g.fold_name("瑞光寺")):
         [("ズイコウジ", "1234567890123", "京都府", "京都市伏見区")]}
TWO_WARDS_SAME = {("神戸市", g.fold_name("光明寺")): [
    ("コウミョウジ", "1", "兵庫県", "神戸市西区"),
    ("コウミョウジ", "2", "兵庫県", "神戸市北区"),
]}
TWO_WARDS_DIFF = {("大阪市", g.fold_name("興徳寺")): [
    ("コウトクジ", "1", "大阪府", "大阪市天王寺区"),
    ("オキノリジ", "2", "大阪府", "大阪市北区"),
]}


def rows(city="京都市", ja="瑞光寺", pref="京都府"):
    return [("Q1", ja, city, pref)]


def test_a_single_ward_inside_the_claimed_city_matches():
    lines, stats = g.build(rows(), {}, wards=WARDS)
    assert stats["matched a ward inside the claimed city"] == 1
    assert lines == ['Q1|P1814|"ずいこうじ"|S854|"%s"' % (g.REGISTRY % "1234567890123")]


def test_several_wards_agreeing_on_the_reading_still_match():
    lines, stats = g.build([("Q2", "光明寺", "神戸市", "兵庫県")], {},
                           wards=TWO_WARDS_SAME)
    assert len(lines) == 1 and "こうみょうじ" in lines[0]


def test_several_wards_disagreeing_are_refused():
    """Two different temples of one name in one city. Nothing says which."""
    lines, stats = g.build([("Q3", "興徳寺", "大阪市", "大阪府")], {},
                           wards=TWO_WARDS_DIFF)
    assert lines == []
    assert stats["several wards in the city, readings differ"] == 1


def test_the_prefecture_must_still_agree():
    """The ward rule narrows a claim; it does not cross a prefecture."""
    lines, _ = g.build([("Q4", "瑞光寺", "京都市", "大阪府")], {}, wards=WARDS)
    assert lines == []


def test_only_a_city_claim_opens_the_ward_lookup():
    """⛔ A claim that is already a ward, a town or a village is as precise as the
    registry and must be matched exactly — the lookup is for a claim that is one
    level COARSER, never for one that merely differs."""
    for claim in ("伏見区", "大山崎町", "白川村", "京都府"):
        assert g.wards_inside(claim, "瑞光寺", "京都府", WARDS) == []
    assert g.wards_inside("京都市", "瑞光寺", "京都府", WARDS)


def test_the_exact_match_still_wins():
    """The ward lookup only fires when the (city, name) key MISSES. An exact
    municipality match is never second-guessed by it."""
    # ⚠ The reading has to end in a real 寺 tail or `complete()` refuses it as a
    # stem-only furigana on an ambiguous tail — which is the guard doing its job,
    # and is how this fixture was wrong the first time.
    index = {("京都市", g.fold_name("瑞光寺")): [("ベツノジ", "9", "京都府")]}
    lines, stats = g.build(rows(), index, wards=WARDS)
    assert "べつのじ" in lines[0]
    assert stats["matched a ward inside the claimed city"] == 0


def test_the_lookup_is_absent_by_default():
    """`wards=None` must behave exactly as before this existed."""
    lines, stats = g.build(rows(), {})
    assert lines == [] and stats["no match in the registry"] == 1


# --------------------------------------------------------------------------
# ⛔ The refusal, which is the half that looks like the fix
# --------------------------------------------------------------------------
def test_a_disagreeing_municipality_is_never_resolved_by_prefecture():
    """本行寺 is in 墨田区 on Wikidata and the registry's only 東京都 本行寺 is in
    小平市. A temple in Sumida is not a temple in Kodaira, and the name being
    unique in Tokyo says nothing about whether it is the same temple.

    Measured over the real data: 1,959 unique-in-prefecture plus 1,420 whose
    several entries share one reading = **3,379** candidates this would have
    emitted, each cited to a stranger's corporate number.
    """
    index = {("小平市", g.fold_name("本行寺")): [("ホンギョウジ", "1", "東京都")]}
    lines, stats = g.build([("Q5", "本行寺", "墨田区", "東京都")], index, wards={})
    assert lines == []
    assert stats["no match in the registry"] == 1


def test_the_measurement_is_recorded_where_it_will_be_read():
    """The next session to have this idea should find it already answered, in the
    generator's own docstring rather than only in DEVLOG."""
    assert "do not re-propose" in g.__doc__.lower()
    assert "3,379" in g.__doc__


@pytest.mark.parametrize("claimed,registry,inside", [
    ("京都市", "京都市伏見区", True),
    ("名古屋市", "名古屋市東区", True),
    ("神戸市", "神戸市西区", True),
    ("京都市", "小平市", False),
    ("墨田区", "小平市", False),
])
def test_the_containment_is_structural_not_substring(claimed, registry, inside):
    """`城陽市` is not inside `京都市` and no substring test should imply it is —
    the match is city + a ward suffix, parsed, not `in`."""
    m = g._CITY_WARD.match(registry)
    assert bool(m and m.group(1) == claimed) is inside
