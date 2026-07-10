"""Tests for generate_religious_building_labels pure logic (no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_religious_building_labels import (  # noqa: E402
    is_latin_script, commons_to_english,
)


def test_latin_script_accepts_latin_with_punct():
    assert is_latin_script("St Mary's Church, Oxford")
    assert is_latin_script("Sagrada Família")          # diacritics are Latin
    assert is_latin_script("Notre-Dame de Paris")


def test_latin_script_rejects_non_latin():
    assert not is_latin_script("Собор")                # Cyrillic
    assert not is_latin_script("مسجد")                 # Arabic
    assert not is_latin_script("教会")                  # CJK
    assert not is_latin_script("Ἁγία Σοφία")           # Greek
    assert not is_latin_script("1234 ,.-")             # no letters at all


def test_commons_to_english_strips_category_prefix():
    assert commons_to_english("Category:Cologne Cathedral") == "Cologne Cathedral"


def test_commons_to_english_keeps_comma_disambiguator():
    # comma forms are part of church names, kept
    assert commons_to_english("St Mary's Church, Oxford") == "St Mary's Church, Oxford"


def test_commons_to_english_strips_trailing_bracket():
    assert commons_to_english("Blue Mosque (Istanbul)") == "Blue Mosque"
    assert commons_to_english("Category:Trinity Church [demolished]") == "Trinity Church"


def test_commons_to_english_none_for_non_latin():
    assert commons_to_english("Category:Собор Василия Блаженного") is None
    assert commons_to_english("مسجد السلطان أحمد") is None


def test_commons_to_english_collapses_whitespace():
    assert commons_to_english("Category:St   Paul's   Cathedral") == "St Paul's Cathedral"
