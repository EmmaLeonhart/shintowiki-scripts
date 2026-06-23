"""Tests for the temple multilingual framework.

Emma's rule (2026-06-23): every language transliterates the name AND adds its
word for "(Buddhist) temple" — even though most real Wikidata labels drop the
word. Plus: the English-source SPARQL must include Japanese temples, not just
shrines.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import format_label, make_sparql_en  # noqa: E402


def test_en_source_sparql_includes_japanese_temples():
    q = make_sparql_en("de")
    assert "wd:Q5393308" in q and "wd:Q17" in q   # Buddhist temple in Japan
    assert "wd:Q845945" in q                       # still includes shrines


# Every covered language must add a temple word (transliterate + word), not a
# shrine word and not nothing. Spot-check across scripts/positions, incl. the
# gap fixes (da/el/hu/ms/mr/nb/br/eo/tl/war/jv/min).
TEMPLE_EXPECTED = {
    "de": "Kinkaku-ji-Tempel",
    "fr": "Temple Kinkaku-ji",
    "es": "Templo Kinkaku-ji",
    "it": "Tempio Kinkaku-ji",
    "vi": "Chùa Kinkaku-ji",
    "ru": "Храм Кинкакудзи",
    "el": "Ναός Κινκακουτζι",
    "da": "Kinkaku-ji-tempel",
    "nb": "Kinkaku-ji-tempel",
    "hu": "Kinkaku-ji-templom",
    "eo": "Templo Kinkaku-ji",
    "tl": "Templo Kinkaku-ji",
    "war": "Templo Kinkaku-ji",
    "br": "Templ Kinkaku-ji",
    "ms": "Wihara Kinkaku-ji",
    "jv": "Wihara Kinkaku-ji",
    "min": "Wihara Kinkaku-ji",
    "mr": "किनाकाकुजि मंदिर",
}


def test_temple_labels_have_a_temple_word_per_language():
    for lang, expected in TEMPLE_EXPECTED.items():
        assert format_label(lang, "Kinkaku-ji", False, "temple") == expected, lang


def test_gap_languages_no_longer_use_a_shrine_word():
    # da/nb shrine word was "helligdommen"; el was "Ιερό"; hu "szentély";
    # ms/jv/min "Kuil"; war "Santuario"; tl "Dambanang"; br "Santual".
    for lang, shrine_word in [("da", "helligdommen"), ("nb", "helligdommen"),
                              ("el", "Ιερό"), ("hu", "szentély"), ("ms", "Kuil"),
                              ("war", "Santuario"), ("tl", "Dambanang"), ("br", "Santual")]:
        out = format_label(lang, "Kinkaku-ji", False, "temple")
        assert shrine_word not in out, (lang, out)
