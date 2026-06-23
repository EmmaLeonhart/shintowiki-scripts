"""Tests for temple_english — deterministic kana -> English temple label.

Encodes Emma's temple convention (2026-06-23): "<Stem>-<suffix> Temple", with the
suffix romanized from the kana so the actual reading is preserved. Conservative:
unknown suffix, suffix/kana mismatch, unromanizable or empty stem -> None.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temple_english import label_for, strip_brackets  # noqa: E402


# ---- the dominant case: 寺 read じ -> "<Stem>-ji Temple" ----

def test_ji_basic():
    # 誓願寺 / せいがんじ  (a real item from the worklist)
    assert label_for("誓願寺", "せいがんじ").label == "Seigan-ji Temple"

def test_ji_famous():
    assert label_for("金閣寺", "きんかくじ").label == "Kinkaku-ji Temple"

def test_ji_long_vowel_collapsed():
    # 東大寺 / とうだいじ : とうだい -> Todai (long o collapsed)
    assert label_for("東大寺", "とうだいじ").label == "Todai-ji Temple"


# ---- 寺 read でら / てら : preserve the actual reading ----

def test_dera_reading_preserved():
    assert label_for("清水寺", "きよみずでら").label == "Kiyomizu-dera Temple"

def test_dera_beats_ji_ordering():
    # でら must be tried before じ so the reading is kept, not truncated wrong.
    assert label_for("長谷寺", "はせでら").label == "Hase-dera Temple"


# ---- 院 read いん ----

def test_in_suffix():
    assert label_for("三千院", "さんぜんいん").label == "Sanzen-in Temple"


# ---- 庵 read あん ----

def test_an_suffix():
    assert label_for("寂庵", "じゃくあん").label == "Jaku-an Temple"


# ---- katakana kana is normalised ----

def test_katakana_input():
    assert label_for("金閣寺", "キンカクジ").label == "Kinkaku-ji Temple"


# ---- bracket stripping ----

def test_strip_brackets_fullwidth():
    assert strip_brackets("誓願寺（京都市）") == "誓願寺"

def test_strip_brackets_halfwidth():
    assert strip_brackets("誓願寺 (Kyoto)") == "誓願寺"

def test_label_strips_brackets_before_processing():
    assert label_for("金閣寺（鹿苑寺）", "きんかくじ").label == "Kinkaku-ji Temple"


# ---- conservative: None rather than a wrong label ----

def test_non_temple_kanji_returns_none():
    # 教会 = church; slipped into the temple set, must not be labelled.
    assert label_for("日蓮宗三世院教会", "にちれんしゅうさんぜいんきょうかい") is None

def test_suffix_kana_mismatch_returns_none():
    # ja ends 寺 but kana ends いん -> mismatch, defer.
    assert label_for("妙法寺", "みょうほういん") is None

def test_empty_stem_returns_none():
    # just the suffix, no stem.
    assert label_for("寺", "じ") is None

def test_unromanizable_stem_returns_none():
    # kanji left in the reading -> romanize fails -> None.
    assert label_for("漢寺", "漢じ") is None

def test_generic_jiin_returns_none():
    assert label_for("○○寺院", "まるまるじいん") is None

def test_empty_inputs_return_none():
    assert label_for("", "") is None
    assert label_for("金閣寺", "") is None
