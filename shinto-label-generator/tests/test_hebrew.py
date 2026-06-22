"""Hebrew (he) label generation (B3 script map). Convention from existing labels:
"מקדש <Name>", name transliterated to the Hebrew abjad (a→א, u/o→ו, i→י, ya→י).
The expected strings below are the ACTUAL Wikidata labels — the map must
reproduce them (verification gate)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, hebraify, ALL_LANGS  # noqa: E402

MIQDASH = "מקדש"


def _is_hebrew(s):
    return all(ch == " " or 0x0590 <= ord(ch) <= 0x05FF for ch in s)


def test_he_in_all_langs():
    assert "he" in ALL_LANGS


def test_reproduces_real_labels():
    # ground truth from Wikidata: מקדש סאנו / יסוקוני / האקוטו / איסה
    assert hebraify("Sano") == "סאנו"
    assert hebraify("Yasukuni") == "יסוקוני"
    assert hebraify("Hakuto") == "האקוטו"
    assert hebraify("Ise") == "איסה"


def test_format_label_he_prefix():
    label = format_label("he", "Sano", False, "shrine")
    assert label == f"{MIQDASH} סאנו"
    assert _is_hebrew(label)
