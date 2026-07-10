"""commons_normalize — Commons category name → house-style English label.

Spec: docs/superpowers/specs/2026-07-10-commons-romaji-normalization-design.md
Mid-pipeline fallback (fires after existing-label + kana derivation). Japanese shrines +
temples only. Transcribes a *marked* long vowel (Sensouji→Sensō-ji), never guesses an
unmarked one (Sensoji→Senso-ji, the acceptable missed macron). Conservative: junk → None.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import commons_normalize as cn  # noqa: E402


# ─────────────── the two canonical cases (Emma, 2026-07-10) ───────────────

def test_marked_long_vowel_becomes_macron():
    assert cn.normalize("Sensouji") == "Sensō-ji Temple"


def test_unmarked_long_vowel_is_left_plain():
    assert cn.normalize("Sensoji") == "Senso-ji Temple"


# ─────────────── the long-vowel transcriber in isolation ───────────────

def test_transcribe_ou_to_o_macron():
    assert cn.transcribe_long_vowels("sensou") == "sensō"


def test_transcribe_uu_to_u_macron():
    assert cn.transcribe_long_vowels("juu") == "jū"


def test_transcribe_oo_to_o_macron():
    assert cn.transcribe_long_vowels("tookyoo") == "tōkyō"


def test_transcribe_leaves_a_bare_vowel_alone():
    assert cn.transcribe_long_vowels("senso") == "senso"


# ─────────────── temple suffixes → "<Stem>-<suffix> Temple" ───────────────

def test_category_prefix_is_stripped():
    assert cn.normalize("Category:Kiyomizu-dera") == "Kiyomizu-dera Temple"


def test_dera_suffix():
    assert cn.normalize("Kiyomizu-dera") == "Kiyomizu-dera Temple"


def test_in_suffix():
    assert cn.normalize("Sanzen-in") == "Sanzen-in Temple"


def test_dera_beats_ji_because_longer_endings_win_first():
    # "-dera" ends in ...a not ...ji, but the ordering guard matters for names like this
    assert cn.normalize("Hase-dera") == "Hase-dera Temple"


def test_a_macroned_temple_name_is_kept():
    assert cn.normalize("Tōfuku-ji") == "Tōfuku-ji Temple"


# ─────────────── shrine forms (kana_english house table) ───────────────

def test_jinja_becomes_shrine():
    assert cn.normalize("Yasukuni Jinja") == "Yasukuni Shrine"


def test_jingu_becomes_grand_shrine():
    assert cn.normalize("Meiji Jingu") == "Meiji Grand Shrine"


def test_jingu_with_macron_also_grand_shrine():
    assert cn.normalize("Meiji Jingū") == "Meiji Grand Shrine"


def test_taisha_becomes_grand_shrine():
    assert cn.normalize("Izumo-taisha") == "Izumo Grand Shrine"


def test_attached_gu_suffix():
    assert cn.normalize("Kotohira-gu") == "Kotohira-gu Shrine"


def test_taisha_beats_the_attached_sha_suffix():
    # "taisha" ends in "sha"; the longer shrine word must win, not "<Stem>-sha Shrine"
    assert cn.normalize("Fushimi Inari-taisha") == "Fushimi Inari Grand Shrine"


# ─────────────── already-suffixed input is kept ───────────────

def test_already_english_shrine_is_kept():
    assert cn.normalize("Meiji Shrine") == "Meiji Shrine"


def test_already_english_temple_is_kept():
    assert cn.normalize("Kōfuku-ji Temple") == "Kōfuku-ji Temple"


# ─────────────── disambiguators ───────────────

def test_parenthetical_disambiguator_is_stripped():
    assert cn.normalize("Kasuga-taisha (Nara)") == "Kasuga Grand Shrine"


def test_fullwidth_disambiguator_is_stripped():
    assert cn.normalize("Hikawa-jinja（Ōmiya）") == "Hikawa Shrine"


# ─────────────── conservatism: not-in-scope → None ───────────────

def test_a_church_returns_none():
    assert cn.normalize("Matthäuskirche") is None


def test_a_deity_name_returns_none():
    assert cn.normalize("Amaterasu") is None


def test_an_empty_name_returns_none():
    assert cn.normalize("") is None
    assert cn.normalize("Category:") is None


def test_a_bare_suffix_with_no_stem_returns_none():
    assert cn.normalize("-ji") is None
    assert cn.normalize("Jinja") is None
