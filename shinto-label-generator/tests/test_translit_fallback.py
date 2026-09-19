"""No dedication means transliteration (Emma, 2026-09-18).

`dedication()` refuses the moment ONE name token is absent from `NAMES`, and over
the 22,548-item corpus that was the pipeline's single biggest gate: **13,470
items** refused against 7,599 resolved. `Santo André de Lourizán` is not an
unknown saint — it is Andrew, at a place the table has never heard of.

What these tests hold down is mostly what was wrong first, each found by reading
the output rather than the code:

  * **The qualifier was glued onto the saint's name.** `San Francesco di Paola`
    came out 聖フランチェスコ・パオーラ — a person called Francesco Paola. The
    shape the generic-title branch already emits is the right one:
    `<qualifier>の<聖><dedicatee>`, as in ペーロの聖母教会.
  * **The place was named twice, in two different spellings.**
    `Church of Santa Clara, Vitoria-Gasteiz` read
    ビトリア＝ガステイスのヴィトーリア・ガーステイスの聖クラーラ教会, because the
    first spelling is Wikidata's ja label and the second is derived.
  * **The table lookup did not fold accents** where `dedication()` does, so
    `lucía` missed a saint the table has had all along — 200-odd items that would
    have been READ instead of NAMED.
  * **Type words were being read as dedicatees.** `Església` (Catalan church),
    `gereja` (Indonesian), `hermitage`, `convento`, `parroquia`.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import religious_building_morphemes as m  # noqa: E402

CHURCH = "Q16970"
CHAPEL = "Q108325"


# --------------------------------------------------------------------------
# Emma's own example, which is the acceptance test
# --------------------------------------------------------------------------
def test_her_example():
    """`Santo André de Lourizán` — Andrew, at a place the table cannot name."""
    assert m.render("Santo André de Lourizán", CHURCH, "ja",
                    place="ポンテベドラ", rules="es",
                    place_en="Pontevedra") == "ポンテベドラのロウリーサンの聖アンデレ教会"


def test_the_gate_it_replaces_still_refused_before_the_fallback():
    """`dedication()` itself is unchanged and still returns None here."""
    assert m.dedication("Santo André de Lourizán", "ja", "es") is None


# --------------------------------------------------------------------------
# The slot order — qualifier, THEN the dedicatee
# --------------------------------------------------------------------------
def test_a_qualifier_is_not_part_of_the_saints_name():
    """`San Francesco di Paola` is Francis OF Paola, not Francesco Paola."""
    assert m.render("San Francesco di Paola", CHURCH, "ja", place="パルティニーコ",
                    rules="it") == "パルティニーコのパオーラの聖フランチェスコ教会"


def test_the_shape_matches_the_generic_title_branch():
    """Same slots the Madonna qualifiers already ship with: <qual>の<ded>."""
    assert m.render("Santa Maria della Grazia", CHURCH, "ja", place="ヴェネツィア",
                    rules="it") == "ヴェネツィアのグラーツィアの聖マリア教会"


def test_of_before_any_name_does_not_split():
    """The `of` in `Church of Santa Clara` links the TYPE to the dedicatee."""
    head, qual, saw = m._dedicatee_split("Church of Santa Clara")
    assert head == ["clara"] and qual == [] and saw


def test_a_comma_splits():
    head, qual, _ = m._dedicatee_split("Church of Santa Clara, Vitoria-Gasteiz")
    assert head == ["clara"] and qual == ["vitoria", "gasteiz"]


def test_a_saint_marker_after_the_split_does_not_make_the_place_a_saint():
    """`Chapel of St Anne in San Pedro` — Anne, in a town called San Pedro."""
    head, qual, saw = m._dedicatee_split("Chapel of St Anne in San Pedro")
    assert head == ["anne"] and qual == ["pedro"] and saw
    assert m.render("Chapel of St Anne in San Pedro", CHAPEL, "ja",
                    place="ブエノスアイレス", rules="es").count("聖") == 1


# --------------------------------------------------------------------------
# The place is not named twice
# --------------------------------------------------------------------------
def test_a_qualifier_that_is_the_place_is_dropped():
    assert m.render("Church of Santa Clara, Vitoria-Gasteiz", CHURCH, "ja",
                    place="ビトリア＝ガステイス", rules="es",
                    place_en="Vitoria-Gasteiz") == "ビトリア＝ガステイスの聖クラーラ教会"


def test_the_comparison_is_against_the_english_label():
    """Without `place_en` there is nothing in the same alphabet to compare to,
    so the qualifier stays — the guard never guesses."""
    out = m.render("Church of Santa Clara, Vitoria-Gasteiz", CHURCH, "ja",
                   place="ビトリア＝ガステイス", rules="es")
    assert out and "ヴィトーリア" in out


def test_a_label_that_is_only_the_place_gives_place_plus_type():
    """`Pančevo Synagogue` in Pančevo — nothing left for the dedication slot.
    Same call `render_mosque` makes for `Mosque in Pirshagi`."""
    assert m.transliterate_dedication("Pančevo Synagogue", "ja",
                                      latin_rules="bs",
                                      place_en="Pančevo") == m.PLACE_ONLY


def test_a_label_with_no_name_at_all_is_still_refused():
    """`Kirche` is not named after its place, it is not named. Different thing."""
    assert m.render("Kirche", CHURCH, "ja", place="タントウ", rules="it") is None


# --------------------------------------------------------------------------
# ja only — the same line `_QUALIFIER_LANGS` and `_MOSQUE_NAME_LANGS` hold
# --------------------------------------------------------------------------
@pytest.mark.parametrize("lang", ["zh", "ko"])
def test_no_transliteration_into_hanzi_or_hangul(lang):
    assert m.render("Santo André de Lourizán", CHURCH, lang, place="X",
                    rules="es", place_en="Pontevedra") is None
    assert m.transliterate_dedication("San Francesco di Paola", lang,
                                      rules="it") is None


def test_an_unlisted_country_refuses_rather_than_guessing():
    """Emma's other two examples are German and French. `rules_for_country`
    returns None for both, and None must mean refuse, not a default.

    ⚠ `render`'s own signature default is `rules="it"`, which the table path's
    qualifier branch needs for direct calls. The GENERATOR never relies on it —
    it passes `rules=_rules_for(p17)`, i.e. None — and this test exercises that,
    because passing no rules at all reads Jördenstorf as if it were Italian,
    which is precisely the confident-wrong failure `rules_for_country` exists to
    refuse.
    """
    import romance_katakana
    import plain_latin_katakana
    for country in ("Q183", "Q142"):          # Germany, France
        assert romance_katakana.rules_for_country(country) is None
        assert plain_latin_katakana.rules_for_country(country) is None
    assert m.render("Dorfkirche Jördenstorf", CHURCH, "ja",
                    place="テッセン", rules=None) is None
    assert m.render("Église du Pras de La Mulatière", CHURCH, "ja",
                    place="リヨン", rules=None) is None


def test_all_or_nothing():
    """A qualifier that cannot be read refuses the label rather than being
    dropped — `_qualifier_residue` makes the same call, for the same reason."""
    assert m.transliterate_dedication("San Pietro di Rzhavets", "ja",
                                      rules="it") is None


# --------------------------------------------------------------------------
# The table lookup folds; the transliterator does not
# --------------------------------------------------------------------------
@pytest.mark.parametrize("label,expect", [
    ("Iglesia de Santa Lucía", "聖ルチア"),
    ("Igreja de Santo António", "聖アントニオ"),
    ("Iglesia de San Francisco", "聖フランチェスコ"),
])
def test_an_accented_spelling_finds_the_table_entry(label, expect):
    out = m.render(label, CHURCH, "ja", place="セビリア", rules="es")
    assert out == "セビリア" + "の" + expect + "教会"


def test_one_saint_never_gets_two_japanese_forms():
    """`francesco` was フランチェスコ from the table while `francisco`, absent,
    was read as フランシースコ."""
    assert m.NAMES["francisco"] == m.NAMES["francesco"]
    for variant, canonical in (("agata", "agatha"), ("tommaso", "thomas"),
                               ("benedetto", "benedict"), ("ana", "anna"),
                               ("nicolò", "nicola"), ("margherita", "margaret"),
                               ("cristo", "christus"), ("vito", "vitus")):
        assert m.NAMES[variant] == m.NAMES[canonical]


def test_a_saint_the_table_does_not_name_is_read_not_named():
    """Absent is what the fallback is FOR. Gregorio is not in `NAMES` and must
    not be quietly added to it by this work."""
    assert "gregorio" not in m.NAMES
    out = m.render("San Gregorio", CHURCH, "ja", place="ローマ", rules="it")
    assert out and out.startswith("ローマの聖") and out.endswith("教会")


# --------------------------------------------------------------------------
# Type words are frame, not dedicatees
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word", ["església", "esglesia", "gereja", "hermitage",
                                  "convento", "parroquia", "ermida", "santuario"])
def test_leaking_type_words_are_frame(word):
    assert word in m.TYPE_WORDS
    head, _, _ = m._dedicatee_split("%s de San Pedro" % word)
    assert head == ["pedro"]


def test_an_accented_frame_word_is_folded():
    """`apóstol` is in STOPWORDS as `apostol` and was reaching the name slot."""
    head, _, _ = m._dedicatee_split("Iglesia de San Pedro Apóstol")
    assert head == ["pedro"]


# --------------------------------------------------------------------------
# The existing paths are untouched
# --------------------------------------------------------------------------
def test_a_known_dedication_still_goes_through_the_table():
    assert m.render("St. Laurentius", CHURCH, "ja",
                    place="レーデン") == "レーデンの聖ラウレンティウス教会"
    assert m.render("St. Laurentius", CHURCH, "zh", place="雷登") == "雷登圣老楞佐教堂"


def test_a_category_shaped_label_is_still_refused():
    assert m.render("Cultural heritage monuments in Lourizán", CHURCH, "ja",
                    place="ポンテベドラ", rules="es") is None


def test_the_place_is_still_mandatory():
    assert m.render("Santo André de Lourizán", CHURCH, "ja", place=None,
                    rules="es") is None
