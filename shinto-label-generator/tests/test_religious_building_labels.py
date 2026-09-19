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


# ---------------------------------------------------------------------------
# The Latin-script gate STAYS. Pinned 2026-09-19 with the measurement, because
# "drop the gate and transliterate Arabic/Hebrew/Devanagari" reached queue.md
# once already and the behaviour was pinned while the REASON was not.
# ---------------------------------------------------------------------------
def test_the_gate_still_refuses_the_three_scripts_a_queue_item_wanted_opened():
    """⛔ Arabic and Hebrew omit short vowels, so a romaniser INVENTS them.
    Measured with aksharamukha, which this repo already depends on:
        مسجد النور    (Masjid al-Nur)        -> masajada alanav̈ara
        בית הכנסת הגדול (Beit HaKnesset HaGadol) -> vĕyt hĕk͟hnĕst hĕgdĕvl
    That is the confident-wrong failure romance_katakana.rules_for_country and
    plain_latin_katakana's refusals exist to prevent."""
    assert commons_to_english("Category:مسجد النور") is None
    assert commons_to_english("Category:בית הכנסת הגדול") is None
    assert commons_to_english("Category:श्री राम मन्दिर") is None


def test_the_gate_lets_through_what_the_item_claimed_it_blocked():
    """The premise was "no Arab-world mosques and no Hebrew-named synagogues at
    all: never selected". Measured over the corpus: 16 Arab-world mosques and 451
    synagogues ARE selected. Their Commons categories are Latin, like these."""
    assert commons_to_english("Category:Masjid al-Hudaibiyah") == "Masjid al-Hudaibiyah"
    assert commons_to_english("Category:Queen Arwa mosque, Jibla") == "Queen Arwa mosque, Jibla"
    assert commons_to_english("Category:Synagogue in Nýrsko") == "Synagogue in Nýrsko"


def test_the_output_path_is_the_paused_directory():
    """⛔ The 2026-09-17 pause moved the file with `git mv` and unwired CI, but never
    touched this constant — it still said `quickstatements/`, the one directory
    `select_label_proposals.py` globs. A hand-run would have put all 22,548 paused
    labels straight back on the drip. `test_no_workflow_regenerates_a_paused_file`
    cannot catch that, because a hand-run is not a workflow."""
    import generate_religious_building_labels as gen
    parts = os.path.normpath(gen.OUT).split(os.sep)
    assert parts[-2:] == ["paused", "religious_building_en.txt"], gen.OUT


def test_the_docstring_says_the_script_is_paused():
    """The docstring described a live stage-1 pipeline and said stage 2 was "to come".
    Both were two months stale, and reading it is how the drop-the-gate item got
    written in the first place."""
    import generate_religious_building_labels as gen
    assert "PAUSED" in gen.__doc__
    assert "paused/README.md" in gen.__doc__
