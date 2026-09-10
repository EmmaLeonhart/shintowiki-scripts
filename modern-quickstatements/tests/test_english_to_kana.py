"""Tests for english_to_kana — the inverse of kana_english.

The module writes readings onto Wikidata via the QuickStatements drip, so the
tests that matter most are the REFUSALS: every case it declines is an item left
alone instead of given a guessed reading.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kana_english  # noqa: E402
from english_to_kana import kana_for, romaji_to_hiragana  # noqa: E402


@pytest.mark.parametrize("romaji,expected", [
    ("Kasano", "かさの"),
    ("Kasuga", "かすが"),
    ("Takuzudama", "たくずだま"),
    ("Futonorito", "ふとのりと"),
    ("Isobe", "いそべ"),
    ("Ginzan", "ぎんざん"),      # moraic nasal before a consonant
    ("Shinmei", "しんめい"),      # moraic nasal before m
    ("Hachiman", "はちまん"),     # word-final moraic nasal
    ("Nikko", "にっこ"),          # geminate
    ("Shin'ichi", "しんいち"),    # apostrophe separates ん from a vowel mora
    ("Kyoto", "きょと"),          # yoon, longest-mora-first
])
def test_romaji_to_hiragana(romaji, expected):
    assert romaji_to_hiragana(romaji) == expected


@pytest.mark.parametrize("bad", ["Zeb", "", "   ", None])
def test_romaji_to_hiragana_refuses_impossible(bad):
    """A stranded consonant is not Japanese phonology — romaji_phonology exists
    to reject exactly this, and the inverse table must not invent a mora for it."""
    assert romaji_to_hiragana(bad) is None


def test_round_trip_through_kana_english():
    """Anything kana_english romanizes, this must read back. Long vowels are the
    known exception (the label is macron-free), so they are not asserted here."""
    for kana in ["かさの", "たくずだま", "ふとのりと", "いそべ", "ぎんざん", "はちまん"]:
        romaji = kana_english.romanize(kana)
        assert romaji_to_hiragana(romaji) == kana, (kana, romaji)


@pytest.mark.parametrize("ja,en,expected", [
    ("多久頭魂神社", "Takuzudama Shrine", "たくずだまじんじゃ"),
    ("太祝詞神社", "Futonorito Shrine", "ふとのりとじんじゃ"),
    ("笠野神社", "Kasano Shrine", "かさのじんじゃ"),
    ("春日神社", "Kasuga Shrine", "かすがじんじゃ"),
    # the parenthetical disambiguator is not part of the name
    ("笠野神社", "Kasano Shrine (Kaga Province)", "かさのじんじゃ"),
    ("いそ部神社", "Isobe Shrine (Miwakare Park)", "いそべじんじゃ"),
])
def test_kana_for(ja, en, expected):
    assert kana_for(ja, en) == expected


def test_kasuga_matches_emmas_ruling():
    """Emma, 2026-08-24, on Q135935015: "this one in katakana is just an error"
    -> かすがじんじゃ. The derivation has to land on exactly that."""
    assert kana_for("春日神社", "Kasuga Shrine") == "かすがじんじゃ"


def test_tenjinsha_is_not_stripped_as_plain_shrine():
    """The 天神社 trap: the split is 天神 + 社, not 天 + 神社. Stripping " Shrine"
    and appending じんじゃ would emit あなざわてんじんじんじゃ."""
    got = kana_for("穴沢天神社", "Anazawa Tenjin Shrine")
    assert got == "あなざわてんじんじゃ"
    assert "じんじんじゃ" not in got


@pytest.mark.parametrize("ja,en,why", [
    ("座摩神", "Ikasuri no Kami", "~神 is not a shrine-type suffix; Emma ruled 四至神 correct as it stands"),
    ("四至神", "Miyanomeguri-no-Kami", "same shape, explicitly ruled correct"),
    ("岩井温泉", "Iwai Onsen", "an onsen, not a shrine"),
    ("一之宮神社", "Ichinomiya Shrine Yokohama", "multi-word stem: a disambiguator, not a name"),
    ("嶋大國魂御子神社", "Shima Okunitama Miko Shrine", "multi-word stem"),
    ("出雲大社", "Izumo Grand Shrine", "大社 reads いずもおおやしろ here; English cannot tell"),
    ("石清水八幡宮", "Iwashimizu Hachimangu Grand Shrine", "English does not end in a known suffix"),
    ("春日神社", "", "no English label"),
    ("", "Kasuga Shrine", "no Japanese label"),
])
def test_kana_for_refuses(ja, en, why):
    assert kana_for(ja, en) is None, why
