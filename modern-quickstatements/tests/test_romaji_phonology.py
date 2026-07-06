"""Tests for romaji_phonology — Japanese-mora validator (queue #8)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from romaji_phonology import is_valid_label, is_valid_romaji_mora  # noqa: E402


# ---- valid romaji stems ----

def test_mefu_valid():
    assert is_valid_romaji_mora("Mefu")          # me + fu

def test_kasuga_valid():
    assert is_valid_romaji_mora("Kasuga")

def test_geminate_valid():
    assert is_valid_romaji_mora("Nikko")         # ni + っ + ko
    assert is_valid_romaji_mora("Hattori")       # ha + っ + to + ri

def test_moraic_n_valid():
    assert is_valid_romaji_mora("Tenjin")        # te + n + ji + n
    assert is_valid_romaji_mora("Shinto")        # shi + n + to

def test_long_vowel_and_macron_valid():
    assert is_valid_romaji_mora("Kyoto")         # kyo + to
    assert is_valid_romaji_mora("Ōsaka")         # macron -> o + saka
    assert is_valid_romaji_mora("Tōkyō")


# ---- invalid romaji: the failure Emma flagged ----

def test_zeb_invalid_b_coda():
    # 'b' cannot close a syllable — only the moraic nasal 'n' can.
    assert not is_valid_romaji_mora("Zeb")

def test_zebsho_invalid():
    assert not is_valid_romaji_mora("Zebshō")

def test_stranded_consonant_invalid():
    assert not is_valid_romaji_mora("Kasg")      # ka + stranded 's','g'


# ---- full-label validation (English type-words skipped) ----

def test_valid_full_labels():
    assert is_valid_label("Mefu Shrine")
    assert is_valid_label("Kasuga Grand Shrine")
    assert is_valid_label("Tenjin-gu Shrine")

def test_invalid_full_label_flags_bad_stem():
    # the real-world garbage label that motivated this validator
    assert not is_valid_label("Zebshō-ji Temple")
