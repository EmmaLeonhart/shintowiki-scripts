"""Tests for the cdo (Min Dong / Bàng-uâ-cê) romanizer.

cdo is NOT a phonetic transliteration of the kana — per Emma's directive it is
the Min Dong reading of the SAME (traditional) Chinese characters the zh
generator produces, one syllable per character, space-joined. It is GATED: a
label is emitted only when EVERY character has a Wiktionary md= reading, so a
partial/wrong romanization is never produced.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_chinese_quickstatements as z  # noqa: E402


def test_readings_table_loaded():
    # The corpus-RAG table is present and non-trivial.
    assert len(z.CDO_READINGS) > 500
    assert z.CDO_READINGS.get("神") == "sìng"


def test_cdoify_basic_shrine_words():
    assert z.cdoify("神社") == "sìng siâ"
    assert z.cdoify("神宮") == "sìng gṳ̆ng"


def test_cdoify_joins_every_char():
    # One syllable per character, in order.
    assert z.cdoify("三神社") == "săng sìng siâ"


def test_cdoify_gated_on_uncovered_char():
    # 龘 (a rare char) has no md= reading → the WHOLE label is withheld (None),
    # never a partial "sìng siâ"-with-a-gap.
    assert z.cdoify("龘神社") is None


def test_cdoify_empty_is_none():
    assert z.cdoify("") is None
    assert z.cdoify(None) is None


def test_cdoify_gates_non_cjk_label():
    # A disambiguated label (parens/space) has no clean char-by-char Bàng-uâ-cê
    # form — it must be WITHHELD, not romanized into stray tokens + double-spaces.
    # (Regression: 2026-07-06 the passthrough branch leaked "sìng siâ ( … )" and
    # tripped the forbidden-whitespace test on cdo.txt.)
    assert z.cdoify("神社（京都府）") is None
    assert z.cdoify("神社 (Kyoto)") is None
    assert z.cdoify("ABC神社") is None


def test_cdoify_first_syllable_only():
    # A stored reading with a slash-variant must collapse to the first syllable,
    # never leaking the "/" or a second reading into the label.
    assert "/" not in (z.cdoify("下") or "")
    assert " " not in (z.cdoify("下") or "x")  # single char → single syllable


def test_cdoify_shinjitai_fallback():
    # 恵 (shinjitai) isn't a table key, but its Chinese-traditional form 惠 is;
    # cdoify must resolve it via the shinjitai map rather than gating the label.
    assert z.CDO_READINGS.get("惠") is not None
    assert z.cdoify("恵") == z.CDO_READINGS["惠"]
