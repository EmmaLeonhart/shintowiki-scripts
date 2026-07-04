"""Rung-2 tier (2026-07-04): pl, ro, fi, cs, sl — both-kind languages that
were missing from format_label. cs/sl ride the new Slavic Latin transcriber;
every transcriber assertion is an observed Wikidata label pair from the
2026-07-04 samples. th deferred (needs a Thai transliterator with vowel
reordering)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import (  # noqa: E402
    ALL_LANGS, czechify, format_label, slovenify,
)
import language_registry as r  # noqa: E402


def test_in_all_langs_and_registry():
    for lang in ["pl", "ro", "fi", "cs", "sl"]:
        assert lang in ALL_LANGS
        assert lang in r.COVERED


# ── czechify: observed cs label pairs ──────────────────────────

def test_czechify_observed_pairs():
    assert czechify("Yasukuni") == "Jasukuni"
    assert czechify("Meiji") == "Meidži"
    assert czechify("Tsurugaoka Hachiman") == "Curugaoka Hačiman"
    assert czechify("Atsuta") == "Acuta"
    assert czechify("Kashihara") == "Kašihara"
    assert czechify("jingū") == "džingú"


def test_czechify_joins_hyphens_and_accents():
    assert czechify("Enryaku-ji") == "Enrjakudži"
    assert czechify("Byōdō-in") == "Bjódóin"
    assert czechify("Kinkaku-ji") == "Kinkakudži"


# ── slovenify: observed sl label pairs ─────────────────────────

def test_slovenify_observed_pairs():
    assert slovenify("Yakushi-ji") == "Jakuši-dži"
    assert slovenify("Tōdai-ji") == "Todai-dži"
    assert slovenify("Kiyomizu") == "Kijomizu"
    assert slovenify("Hachimangū") == "Hačimangu"


# ── format_label wiring ────────────────────────────────────────

def test_pl_prefix_both_kinds():
    assert format_label("pl", "Kasuga", False, "shrine") == "Świątynia Kasuga"
    assert format_label("pl", "Kasuga", False, "temple") == "Świątynia Kasuga"
    assert format_label("pl", "Izumo", True, "shrine") == "Wielka świątynia Izumo"


def test_ro_distinct_words():
    assert format_label("ro", "Kasuga", False, "shrine") == "Sanctuarul Kasuga"
    assert format_label("ro", "Kasuga", False, "temple") == "Templul Kasuga"
    assert format_label("ro", "Izumo", True, "shrine") == "Marele Sanctuar Izumo"


def test_fi_suffix_distinct_words():
    assert format_label("fi", "Kasuga", False, "shrine") == "Kasuga-pyhäkkö"
    assert format_label("fi", "Kasuga", False, "temple") == "Kasuga-temppeli"


def test_cs_transcribed_with_words():
    assert format_label("cs", "Yasukuni", False, "shrine") == "Svatyně Jasukuni"
    assert format_label("cs", "Enryaku-ji", False, "temple") == "Chrám Enrjakudži"


def test_sl_transcribed_with_words():
    assert format_label("sl", "Meiji", False, "shrine") == "Svetišče Meidži"
    assert format_label("sl", "Kiyomizu", False, "temple") == "Tempelj Kijomizu"
    assert format_label("sl", "Sumiyoshi", True, "shrine") == "Veliko svetišče Sumijoši"
