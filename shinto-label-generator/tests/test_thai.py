"""Tests for the Thai (th) transliterator — kana→romaji→Thai via wunsen (Royal Society
standard). The point of Thai is the pre-posed vowel signs (เ/แ/โ/ใ/ไ written before the
consonant, pronounced after), which a naïve char-map can't do — wunsen handles them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_multilang_quickstatements as g  # noqa: E402


def test_th_registered():
    assert "th" in g.ALL_LANGS


def test_thai_shrine_label():
    assert g.format_label("th", "Ise", p_type="shrine") == "ศาลเจ้า อิเซะ"


def test_thai_preposed_vowel():
    # Meiji → เมจิ: the เ vowel is written BEFORE ม but read after — the whole reason
    # a character-by-character map fails for Thai.
    assert g.format_label("th", "Meiji", p_type="shrine") == "ศาลเจ้า เมจิ"


def test_thai_temple_uses_wat():
    assert g.format_label("th", "Sensō", p_type="temple").startswith("วัด")


def test_thaify_handles_long_vowel():
    # Ōmiwa → โอมิวะ (pre-posed โ)
    assert g.thaify("Ōmiwa") == "โอมิวะ"
