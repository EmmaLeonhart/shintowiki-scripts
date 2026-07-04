"""Offline tests for translit_common — the shared bare-name/term transliteration
behind the kami / shrine-rank / province generators. The load-bearing guard is
romaji-source detection: an English gloss ("Three Pioneer Kami") must NOT be
phonetically transliterated (that produced garbage like "Рээ Пионээ Ками");
CJK always comes from the kanji. No network."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from translit_common import (  # noqa: E402
    looks_romaji, romaji_source, bare_name, zh_map, hanja_read, ZH_CODES,
)


# ── looks_romaji: the gate that separates real names from English glosses ──

def test_looks_romaji_accepts_japanese_names():
    assert looks_romaji("Takamimusubi")
    assert looks_romaji("Amaterasu")
    assert looks_romaji("Ōkuninushi")        # macron
    assert looks_romaji("Ame-no-Uzume")      # hyphens
    assert looks_romaji("Susano'o")          # apostrophe


def test_looks_romaji_rejects_english_glosses():
    assert not looks_romaji("Three Pioneer Kami")
    assert not looks_romaji("sun goddess")
    assert not looks_romaji("")


# ── romaji_source: en-if-romaji, else romanise a kana ja, else None ──

def test_romaji_source_prefers_romaji_en():
    assert romaji_source("Amaterasu", "天照大神") == "Amaterasu"


def test_romaji_source_falls_back_to_kana_ja():
    # English gloss en, but a katakana ja label -> romanise the kana
    assert romaji_source("Three Pioneer Kami", "アマテラス") == "amaterasu"


def test_romaji_source_none_for_gloss_plus_kanji():
    # English gloss + kanji (not kana) -> no reliable reading -> None
    assert romaji_source("Three Pioneer Kami", "開拓三神") is None


# ── bare_name: per-script dispatch ──

def test_bare_name_latin_keeps_romaji():
    assert bare_name("de", "Amaterasu", "天照大神") == "Amaterasu"
    assert bare_name("es", "Inari", "稲荷") == "Inari"


def test_bare_name_cyrillic():
    assert bare_name("ru", "Amaterasu", None) == "Аматэрасу"


def test_bare_name_ko_phonetic_vs_hanja():
    assert bare_name("ko", "Amaterasu", "天照大神", ko_mode="phonetic") == "아마테라스"
    assert bare_name("ko", "Kanpei Taisha", "官幣大社", ko_mode="hanja") == "관폐대사"


def test_bare_name_zh_is_none_here():
    # zh family is intentionally handled via zh_map, not bare_name
    for code in ZH_CODES:
        assert bare_name(code, "Amaterasu", "天照") is None


# ── zh_map: from the kanji, all nine zh codes ──

def test_zh_map_from_kanji():
    m = zh_map("官幣大社")
    assert m["zh"] == "官币大社"          # simplified
    assert m["zh-hant"] == "官幣大社"     # traditional
    assert set(ZH_CODES).issubset(m)


def test_zh_map_empty_without_kanji():
    assert zh_map("") == {}
    assert zh_map(None) == {}


# ── hanja_read: sino-Korean reading, None when unresolved ──

def test_hanja_read():
    assert hanja_read("官幣大社") == "관폐대사"
    assert hanja_read("") is None
