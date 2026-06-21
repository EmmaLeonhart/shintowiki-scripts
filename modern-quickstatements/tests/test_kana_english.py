"""Tests for kana_english — deterministic kana -> English shrine label (Stage 1).

Encodes Emma's literal suffix conventions:
    jinja     -> "<Stem> Shrine"
    jingu     -> "<Stem> Grand Shrine"  (+ alias "<Stem> Jingu")
    taisha    -> "<Stem> Grand Shrine"  (+ alias "<Stem> Taisha")
    daijinja  -> "<Stem> Daijinja"
    -sha      -> "<Stem>-sha Shrine"
    -gu       -> "<Stem>-gu Shrine"
Stem is romanized to macron-free Hepburn. Anything we cannot confidently
handle (unknown suffix, unromanizable stem, empty stem) returns None so the
shrine falls through to a later pipeline stage rather than getting a bad label.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kana_english import label_for, romanize  # noqa: E402


# ---- romanize() : kana -> macron-free Hepburn, Title Case ----

def test_romanize_basic():
    assert romanize("かすが") == "Kasuga"

def test_romanize_uses_proper_hepburn_zu_not_su():
    # tokiponizer collapses zu->su; the English romanizer must not.
    assert romanize("みず") == "Mizu"

def test_romanize_shi_chi_tsu():
    assert romanize("しちつ") == "Shichitsu"

def test_romanize_yoon():
    assert romanize("きょうと") == "Kyoto"  # long o collapsed

def test_romanize_long_u_collapsed():
    assert romanize("ぐうう") == "Gu"  # ぐ + うう -> "gu" + "u"

def test_romanize_small_tsu_geminates():
    assert romanize("はっこう") == "Hakko"  # っ doubles k, long o collapsed

def test_romanize_returns_none_on_unmappable():
    assert romanize("かす漢") is None


# ---- label_for(ja, kana) : suffix type from KANJI, stem reading from kana ----

def test_jinja_suffix():
    r = label_for("春日神社", "かすがじんじゃ")
    assert r.label == "Kasuga Shrine"
    assert r.alias is None

def test_taisha_suffix_has_alias():
    r = label_for("春日大社", "かすがたいしゃ")
    assert r.label == "Kasuga Grand Shrine"
    assert r.alias == "Kasuga Taisha"

def test_daijinja_suffix():
    r = label_for("春日大神社", "かすがだいじんじゃ")
    assert r.label == "Kasuga Daijinja"
    assert r.alias is None

def test_bare_sha_suffix():
    # kanji ends in 社 (not 神社) -> "-sha Shrine"
    r = label_for("熊野社", "くまのしゃ")
    assert r.label == "Kumano-sha Shrine"
    assert r.alias is None

def test_bare_gu_suffix():
    # kanji ends in 宮 (not 神宮) -> "-gu Shrine"
    r = label_for("天満宮", "てんまんぐう")
    assert r.label == "Tenman-gu Shrine"
    assert r.alias is None

def test_daijingu_transliterated():
    r = label_for("新潟大神宮", "にいがただいじんぐう")
    assert r.label == "Niigata Daijingu"
    assert r.alias is None

def test_pure_jingu_is_skipped_as_ambiguous():
    # 神宮 stem boundary is ambiguous (Meiji/Jingu vs Tenjin/gu) -> route to Stage 4
    assert label_for("明治神宮", "めいじじんぐう") is None

def test_tenjingu_not_mislabeled_ten_jingu():
    # regression: must NOT strip じんぐう from 天神宮 leaving "Ten"
    assert label_for("天神宮", "てんじんぐう") is None

def test_jinja_beats_bare_sha():
    # 神社 must match before bare 社
    assert label_for("春日神社", "かすがじんじゃ").label == "Kasuga Shrine"

def test_unknown_suffix_returns_none():
    assert label_for("春日山", "かすがやま") is None  # ...yama, not a shrine suffix

def test_empty_stem_returns_none():
    assert label_for("神社", "じんじゃ") is None

def test_unromanizable_stem_returns_none():
    assert label_for("漢字神社", "漢字じんじゃ") is None

def test_kana_reading_mismatch_returns_none():
    # kana doesn't carry the expected suffix reading -> can't get a reliable stem
    assert label_for("春日神社", "かすが") is None
