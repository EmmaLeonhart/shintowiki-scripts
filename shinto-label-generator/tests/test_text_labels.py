"""Tests for generate_text_labels (Emma 2026-07-04: text titles are romaji —
transliterate literally into every target language). Offline: exercises the
routing on canonical cases; engine outputs asserted only where the underlying
engine is already covered by its own tests."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_text_quickstatements import labels_for_item, target_langs  # noqa: E402


def _d(triples):
    # labels_for_item now yields (lang, label, source); collapse to {lang: label}
    return {lang: label for lang, label, *_ in triples}


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


def test_labels_carry_provenance_source():
    # each triple's 3rd element notes where the label derives from
    got = labels_for_item("Engishiki", "延喜式", ["de", "ru", "zh", "ko"])
    src = {lang: source for lang, _label, source in got}
    assert src["de"].startswith("title ")          # Latin verbatim: label IS the title
    assert src["ru"].startswith("romaji ")         # engine lang from the romaji reading
    assert src["zh"].startswith("ja kanji ")       # zh from the kanji
    assert "hanja" in src["ko"]                     # ko sino-Korean reading of the kanji


def test_target_langs_excludes_sources():
    t = target_langs()
    assert "ja" not in t and "en" not in t and "mul" not in t
    assert "de" in t and "zh" in t and "ko" in t


# --- Drip-collision regression (2026-07-04) --------------------------------
# The generic text labeller and the dedicated Shikinaisha-list generator both
# used to emit labels for the 69 "List of Shikinaisha in X" items with DIFFERENT
# values (bare name-transliteration vs a proper descriptive list-title), so which
# one landed depended on random drip order. The text generator now cedes those 69
# items. Guard: no two category .txt files may propose DIFFERENT values for the
# same (qid, lang). Only benign exception — the parent Engishiki Jinmyōchō, whose
# name both files legitimately transliterate, differing only by capitalization.
_QS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "quickstatements")
_CATEGORY_FILES = [
    "kami_labels.txt", "buddhist_deity_labels.txt", "province_labels.txt",
    "human_labels.txt", "text_labels.txt", "misc_term_labels.txt",
    "shikinaisha_lists.txt", "courtrank_labels.txt", "courtrank_translations.txt",
    "concept_translations.txt", "property_translations.txt",
]
_COLLISION_EXEMPT_QIDS = {"Q11064932"}  # Engishiki Jinmyōchō (capitalisation tie)


def test_no_conflicting_labels_across_category_files():
    seen = {}  # (qid, lang) -> (value, filename)
    conflicts = []
    for name in _CATEGORY_FILES:
        path = os.path.join(_QS_DIR, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) < 3 or not parts[1].startswith("L"):
                    continue
                qid, lang, val = parts[0], parts[1], parts[2]
                key = (qid, lang)
                if key in seen and seen[key][0] != val and qid not in _COLLISION_EXEMPT_QIDS:
                    conflicts.append((key, seen[key], (val, name)))
                seen.setdefault(key, (val, name))
    assert not conflicts, (
        f"{len(conflicts)} (qid,lang) proposed with different values across "
        f"category files (drip-order non-determinism); e.g. {conflicts[:3]}")
