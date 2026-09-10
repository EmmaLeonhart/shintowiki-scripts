"""Tests for the general-case derived-kana generator and its long-vowel fix.

Two things are pinned here, and they are the two that a later session could
plausibly undo without noticing:

  1. **A macron is a long vowel, not a short one.** Collapsing ō to o made every
     one of the 506 macron-bearing derivations wrong on the held-out set. The
     おお-vs-おう split is data-derived (see ``_OO_INITIAL``), not a guess.
  2. **Tier 3 does not ship.** Where the name-mate reading contradicts the
     derivation the measured precision is 64%, and Emma's 2026-09-10 call routes
     those to the LLM queue instead. A generator that quietly starts emitting
     them looks identical in every other respect.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import english_to_kana as ek  # noqa: E402
import generate_derived_name_in_kana as gen  # noqa: E402


# ---- long vowels -------------------------------------------------------------

@pytest.mark.parametrize("ja,en,expected", [
    # ō is おう by default -- 黄 reads おう, and the ja label is what says so.
    ("黄金神社", "Ōgon Shrine", "おうごんじんじゃ"),
    ("東郷神社", "Tōgō Shrine", "とうごうじんじゃ"),
    ("加藤神社", "Katō Shrine", "かとうじんじゃ"),
    # ...and おお after a leading kanji that reads おお.
    ("大神神社", "Ōmiwa Shrine", "おおみわじんじゃ"),
    ("大國魂神社", "Ōkunitama Shrine", "おおくにたまじんじゃ"),
    ("太田神社", "Ōta Shrine", "おおたじんじゃ"),
    # ū is うう, which after a yoon is the ordinary long ゅう.
    ("龍頭山神社", "Ryūtōsan Shrine", "りゅうとうさんじんじゃ"),
    # ā/ī mark a vowel collision across a morpheme boundary, not a long vowel;
    # "aa"/"ii" is right for both readings.
    ("三島愛宕神社", "Mishimātago Shrine", "みしまあたごじんじゃ"),
    ("飯盛神社", "Īmori Shrine", "いいもりじんじゃ"),
])
def test_macrons_expand_to_two_morae(ja, en, expected):
    assert ek.kana_for(ja, en) == expected


def test_a_collapsed_macron_would_be_the_old_bug():
    """The regression this fix is for, stated as its own assertion so a revert is
    unmistakable: 大神神社 must not derive おみわじんじゃ."""
    assert ek.kana_for("大神神社", "Ōmiwa Shrine") != "おみわじんじゃ"


def test_oo_initial_only_applies_at_the_stem_start():
    """大 mid-stem is not what the leading-kanji table is about. 大原大宮 keeps the
    おう default on its second ō -- the table reads the FIRST kanji of the ja
    label, and claiming more than that would be inventing alignment."""
    assert ek.expand_long_vowels("ōyamaōmiya", oo_initial=True) == "ooyamaoumiya"


def test_macron_free_labels_are_untouched():
    """The known loss stays a loss: nothing here invents length that the label
    does not write down."""
    assert ek.kana_for("春日神社", "Kasuga Shrine") == "かすがじんじゃ"


# ---- tiering -----------------------------------------------------------------

MATES = {"諏訪神社": {"すわじんじゃ": 40, "すわじんしゃ": 3}}


def _classify(items, mates=MATES):
    return gen.classify(items, mates)


def test_tier_1_is_agreement_with_the_dominant_name_mate():
    rows, _ = _classify([("Q1", "諏訪神社", "Suwa Shrine", "諏訪神社")])
    assert [r[5] for r in rows] == [1]
    assert gen.build_lines(rows) == ['Q1|P1814|"すわじんじゃ"']


def test_tier_2_is_no_name_mate_at_all():
    rows, _ = _classify([("Q2", "笠野神社", "Kasano Shrine", "笠野神社")])
    assert [r[5] for r in rows] == [2]
    assert gen.build_lines(rows) == ['Q2|P1814|"かさのじんじゃ"']


def test_tier_3_disagrees_and_is_NOT_shipped():
    """The name-mates say ごうどじんじゃ, the English label says みかどじんじゃ. 64%
    precision — Emma routed these to the LLM queue, so no line may be emitted."""
    mates = {"神門神社": {"ごうどじんじゃ": 5}}
    rows, _ = gen.classify([("Q3", "神門神社", "Mikado Shrine", "神門神社")], mates)
    assert [r[5] for r in rows] == [3]
    assert gen.build_lines(rows) == []


def test_ship_tiers_is_exactly_one_and_two():
    assert gen.SHIP_TIERS == {1, 2}


def test_tenjin_shrine_is_held_and_tenjin_sha_is_not():
    """天神社 + "Tenjin Shrine" cannot be resolved from the label (both readings
    are attested per item); "Tenjin-sha" is jawiki-backed and ships."""
    rows, reasons = _classify([
        ("Q4", "大嵐天神社", "Ōarashi Tenjin Shrine", "大嵐天神社"),
        ("Q5", "五條天神社", "Gojō Tenjinsha", "五條天神社"),
    ])
    assert [r[0] for r in rows] == ["Q5"]
    assert reasons["held: undecided reading for this ja/en pair"] == 1


# ---- the mate tally ----------------------------------------------------------

def _mate_rows(triples):
    return [{"item": {"value": "http://www.wikidata.org/entity/" + q},
             "ja": {"value": ja}, "kana": {"value": k}} for q, ja, k in triples]


def test_each_item_votes_once_however_many_shrine_classes_it_carries():
    """A duplicated SPARQL row is a second P31, not a second opinion. Counting
    rows would let one item outvote two."""
    mates = gen.collect_mates(_mate_rows([
        ("Q1", "諏訪神社", "すわじんじゃ"), ("Q1", "諏訪神社", "すわじんじゃ"),
        ("Q2", "諏訪神社", "すわじんしゃ"), ("Q3", "諏訪神社", "すわじんしゃ"),
    ]))
    assert gen.dominant(mates, "諏訪神社") == "すわじんしゃ"


def test_katakana_readings_do_not_vote():
    """A katakana value is an ancient reading a different pipeline is relocating.
    Letting it vote would make a modern hiragana derivation look contradicted."""
    mates = gen.collect_mates(_mate_rows([
        ("Q1", "春日神社", "カスガジンジャ"), ("Q2", "春日神社", "かすがじんじゃ"),
    ]))
    assert gen.dominant(mates, "春日神社") == "かすがじんじゃ"


def test_a_spaced_reading_is_the_same_reading():
    mates = gen.collect_mates(_mate_rows([
        ("Q1", "熊野神社", "くまの じんじゃ"), ("Q2", "熊野神社", "くまのじんじゃ"),
    ]))
    assert gen.dominant(mates, "熊野神社") == "くまのじんじゃ"


def test_ties_break_deterministically():
    """WDQS row order is not stable. An unstable tiebreak would flip a tie-1 item
    between tiers 1 and 3 at random and rewrite the file every build."""
    rows = _mate_rows([("Q1", "X神社", "あじんじゃ"), ("Q2", "X神社", "いじんじゃ")])
    first = gen.dominant(gen.collect_mates(rows), "X神社")
    assert first == gen.dominant(gen.collect_mates(list(reversed(rows))), "X神社")


# ---- the shipped file --------------------------------------------------------

BATCH = os.path.join(MQ, "derived_name_in_kana.txt")
DISAGREEMENTS = os.path.join(MQ, "derived_name_in_kana_disagreements.json")


@pytest.mark.skipif(not os.path.exists(BATCH), reason="batch not generated here")
def test_every_shipped_line_is_a_hiragana_p1814_add():
    for line in open(BATCH, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line:
            continue
        qid, prop, value = line.split("|", 2)
        assert qid.startswith("Q") and prop == "P1814"
        assert value.startswith('"') and value.endswith('"')
        assert all("぀" <= ch <= "ゟ" for ch in value[1:-1]), line


@pytest.mark.skipif(not os.path.exists(DISAGREEMENTS), reason="not generated here")
def test_no_disagreement_also_appears_in_the_shipped_batch():
    """The two outputs must be disjoint. If a QID reached both, the item would get
    a reading AND a work-file asking what its reading is."""
    shipped = {ln.split("|")[0] for ln in open(BATCH, encoding="utf-8") if ln.strip()}
    held = {r["qid"] for r in json.load(open(DISAGREEMENTS, encoding="utf-8"))}
    assert not (shipped & held)
