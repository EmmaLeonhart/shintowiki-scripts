"""The kana is what settles the stem boundary (2026-09-19).

`_SUFFIXES` is ordered most-specific-kanji-first and returned **None** the moment
the specific entry's READING did not match — so `大神社 / おおかみしゃ` was
refused, when the reading had just told us the answer: だいじんじゃ it is not, so
it is not 大 + 神社, so it is 大神 + 社, so it is `Okami-sha Shrine`.

⛔ The half of this that is NOT a relaxation: `神宮` still defers, and must. When
the kana DOES match, both parses stay open — 明治/神宮 is Meiji Jingū and 天神/宮
is Tenjin-gū, and じんぐう fits both. Falling through there would read 明治神宮 as
めいじじん + ぐう and emit `Meijijin-gu Shrine`, which is the failure that entry
was written to prevent.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kana_english import label_for, _SUFFIXES, _variant_ok  # noqa: E402


def lab(ja, kana):
    r = label_for(ja, kana)
    return r.label if r else None


# --------------------------------------------------------------------------
# Fall-through: a mismatched reading is EVIDENCE, not a gap
# --------------------------------------------------------------------------
def test_a_mismatched_reading_rules_that_parse_out():
    """大神社 requires だいじんじゃ. The reading is おおかみしゃ, so the item is
    not 大 + 神社 — and the next entry down gets it right."""
    assert lab("大神社", "おおかみしゃ") == "Okami-sha Shrine"


def test_the_canonical_readings_are_untouched():
    assert lab("八坂神社", "やさかじんじゃ") == "Yasaka Shrine"
    assert lab("出雲大社", "いずもたいしゃ") == "Izumo Grand Shrine"
    assert lab("伊勢大神宮", "いせだいじんぐう") == "Ise Daijingu"
    # ⚠ A BARE 大神宮 has no stem left once the suffix is taken off, and an empty
    # stem has always been refused. Asserting a label for it was this test being
    # wrong, not the code.
    assert lab("大神宮", "だいじんぐう") is None


# --------------------------------------------------------------------------
# ⛔ 神宮 still defers, and for the reason it always did
# --------------------------------------------------------------------------
@pytest.mark.parametrize("ja,kana", [
    ("明治神宮", "めいじじんぐう"),
    ("熱田神宮", "あつたじんぐう"),
    ("天神宮", "てんじんぐう"),
])
def test_jingu_is_still_ambiguous_when_the_reading_agrees(ja, kana):
    """⛔ Both parses stay open, so it defers to a later stage. Falling through
    would give `Meijijin-gu Shrine`."""
    assert lab(ja, kana) is None


def test_the_skip_is_checked_after_the_reading_not_before():
    """The ambiguity only exists when the reading FITS. The entry is still
    `skip`, so nothing about the deferral has been relaxed."""
    entry = next(e for e in _SUFFIXES if e[0] == "神宮")
    assert entry[4] == "skip"
    assert lab("明治神宮", "めいじじんぐう") is None


# --------------------------------------------------------------------------
# Variant readings, and the guard on them
# --------------------------------------------------------------------------
@pytest.mark.parametrize("ja,kana,expect", [
    ("八坂神社", "やさかじんしゃ", "Yasaka Shrine"),     # unvoiced, a real variant
    ("坊金神社", "ぼうがねじんしゃ", "Bogane Shrine"),
    ("若宮神社", "わかみやじんしゃ", "Wakamiya Shrine"),
    ("矢放神社", "やはなしじんじや", "Yahanashi Shrine"),  # large や, a typo
    ("堀出神社", "ほりいでじんじじゃ", "Horiide Shrine"),   # doubled じ, a typo
])
def test_a_variant_tail_still_gives_the_right_stem(ja, kana, expect):
    """⛔ Emma, 2026-08-24: an NTA-cited reading is PRESERVED even when it looks
    like a typo. Nothing here changes a stored reading — the STEM is やさか
    whichever tail the registry recorded, so refusing the label threw away
    something the variant never put in doubt."""
    assert lab(ja, kana) == expect


def test_the_variant_is_refused_where_the_other_parse_is_live():
    """⛔ 神社 is essentially always じんじゃ, so an unvoiced じんしゃ is usually
    not a variant at all — it is the ordinary 社/しゃ with a stem ending in 神.
    水神社 / すいじんしゃ is 水神 + 社, and accepting the variant blindly emitted
    `Sui Shrine`."""
    assert lab("水神社", "すいじんしゃ") == "Suijin-sha Shrine"


def test_the_guard_is_on_length_of_what_is_left():
    """One character and the other parse is live; two or more and the stem is a
    real place or name that owns the whole suffix."""
    assert not _variant_ok("水神社", "神社", "じんしゃ",
                           ("じんじゃ", "じんしゃ"))
    assert _variant_ok("八坂神社", "神社", "じんしゃ", ("じんじゃ", "じんしゃ"))


def test_the_canonical_reading_is_never_subject_to_the_guard():
    """A one-character stem with the ORDINARY reading is not ambiguous at all."""
    assert _variant_ok("水神社", "神社", "じんじゃ", ("じんじゃ", "じんしゃ"))
    assert lab("水神社", "すいじんじゃ") == "Sui Shrine"


def test_the_suffix_table_lists_readings_as_tuples():
    for kanji, readings, *_ in _SUFFIXES:
        assert isinstance(readings, tuple) and readings, kanji
        assert all(r for r in readings), kanji
