"""Tests for generate_text_labels (Emma 2026-07-04: text titles are romaji —
transliterate literally into every target language). Offline: exercises the
routing on canonical cases; engine outputs asserted only where the underlying
engine is already covered by its own tests."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_text_quickstatements import labels_for_item, target_langs  # noqa: E402


def _d(pairs):
    return dict(pairs)


def test_romaji_title_covers_latin_engine_zh_ko():
    got = _d(labels_for_item("Engishiki", "延喜式",
                             ["de", "fr", "ru", "cs", "zh", "zh-hant", "gan", "ko", "he"]))
    # Latin: title verbatim
    assert got["de"] == "Engishiki" and got["fr"] == "Engishiki"
    # Engines actually fire (exact forms owned by the engines' own tests)
    assert got["ru"] and got["ru"] != "Engishiki"
    assert got["cs"] and got["he"]
    # zh family from the kanji
    assert got["zh"] == "延喜式" and got["zh-hant"] and got["gan"]
    # ko: sino-Korean hanja reading of 延喜式 (not phonetic)
    assert got["ko"] and all("가" <= c <= "힣" for c in got["ko"])


def test_macrons_kept_in_latin_titles():
    got = _d(labels_for_item("Engishiki Jinmyōchō", "延喜式神名帳", ["de", "pl"]))
    assert got["de"] == "Engishiki Jinmyōchō"


def test_sinitic_title_non_romaji_en_still_gets_zh_ko():
    # "Draft History of Qing" is an English gloss, not romaji — Latin/engine
    # langs must NOT get it, but zh/ko still derive from 清史稿.
    got = _d(labels_for_item("Draft History of Qing", "清史稿",
                             ["de", "ru", "zh", "ko"]))
    assert "de" not in got and "ru" not in got
    assert got["zh"] and got["ko"]


def test_unroutable_item_yields_nothing():
    # No romaji, no kana, no kanji: e.g. an empty-label encyclopedia article.
    assert labels_for_item("", "", ["de", "ru", "zh", "ko"]) == []


def test_target_langs_excludes_sources():
    t = target_langs()
    assert "ja" not in t and "en" not in t and "mul" not in t
    assert "de" in t and "zh" in t and "ko" in t
