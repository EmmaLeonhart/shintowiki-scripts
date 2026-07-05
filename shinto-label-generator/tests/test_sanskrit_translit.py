"""Tests for the SEPARATE Sanskrit transliterator (sanskrit_translit.py) — the
engine behind Sanskrit-named Buddhist deities. Locks in the behaviours Emma
directed: cluster-preserving (no dropping), Devanagari abugida, Greek double-nasal
collapse, Arabic-family word-initial vowel carriers, and toki pona (n-coda +
epenthetic cluster-breaking). Offline, no network."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sanskrit_translit import sanskrit, SUPPORTED  # noqa: E402


# ── Devanagari (native Sanskrit script; proper abugida with virama clusters) ──

def test_devanagari():
    assert sanskrit("Indra", "hi") == "इन्द्र"
    assert sanskrit("Skanda", "hi") == "स्कन्द"     # स्क cluster via virama
    assert sanskrit("Agni", "hi") == "अग्नि"
    assert sanskrit("Brahma", "hi") == "ब्रह्म"


def test_bengali():
    assert sanskrit("Indra", "bn") == "ইন্দ্র"
    assert sanskrit("Skanda", "bn") == "স্কন্দ"


# ── Cyrillic: letter-by-letter, clusters kept, name capitalised ──

def test_cyrillic_capitalised_and_clustered():
    assert sanskrit("Indra", "ru") == "Индра"       # not "индра"
    assert sanskrit("Skanda", "ru") == "Сканда"     # sk cluster survives
    assert sanskrit("Indra", "uk") == "Индра"


# ── Greek: double-nasal collapse (the ντ/μπ/γκ digraph carries the nasal) ──

def test_greek_double_nasal_collapse():
    assert sanskrit("Indra", "el") == "Ιντρα"       # not "Ινντρα"
    assert sanskrit("Skanda", "el") == "Σκαντα"     # not "Σκανντα"
    assert sanskrit("Brahma", "el") == "Μπραχμα"


# ── Arabic-family: word-initial vowel takes a carrier; consonant-initial doesn't ──

def test_arabic_initial_vowel_carrier():
    assert sanskrit("Indra", "ar") == "إندرا"       # initial i -> إ (not يندرا)
    assert sanskrit("Agni", "ar") == "أغني"         # initial a -> أ
    assert sanskrit("Skanda", "ar") == "سكاندا"     # consonant-initial: unchanged


def test_persian_and_hebrew_initial_carrier():
    assert sanskrit("Indra", "fa") == "ایندرا"
    assert sanskrit("Indra", "ur") == "ایندرا"
    assert sanskrit("Indra", "he") == "אינדרא"


# ── Toki Pona: n is a valid coda (nt/nk kept), other clusters get epenthetic 'a' ──

def test_tok_n_coda_and_cluster_breaking():
    assert sanskrit("Indra", "tok") == "Intala"     # -nt- kept, tr -> tala
    assert sanskrit("Skanda", "tok") == "Sakanta"   # sk broken, -nt- kept
    assert sanskrit("Agni", "tok") == "Akani"       # g->k, no cluster


# ── Contract ──

def test_unsupported_lang_and_empty_return_none():
    assert sanskrit("Indra", "de") is None          # Latin langs keep romaji, not here
    assert sanskrit("Indra", "zh") is None
    assert sanskrit("", "hi") is None


def test_supported_set():
    # the transliterating scripts, not Latin/CJK/ko
    assert {"hi", "bn", "ru", "el", "ar", "fa", "he", "tok"}.issubset(SUPPORTED)
    assert "de" not in SUPPORTED and "zh" not in SUPPORTED
