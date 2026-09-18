"""Stage 2: ja/zh/ko labels for religious buildings, composed from morphemes.

What these hold down is mostly the things that were WRONG first, because each was
found by measuring the real 22,548-label corpus rather than by reasoning:

  * **Collisions.** Composing dedication + type alone gave 36 distinct outputs for
    2,392 labels -- 99.6% colliding, 515 Madonna churches all becoming 聖母教会.
    For this population the "name" IS the dedication and hundreds share it, so the
    place is what separates them and `render()` must refuse without one.
  * **Double-rendering.** "San Giovanni Battista" rendered Giovanni AND Battista
    and came out as 聖ヨハネ洗礼者ヨハネ -- John twice.
  * **A fused saint marker.** "Santiago" is Sant+Iago, so no marker token appears
    and the 聖 prefix was dropped.
  * **A leaked disambiguator.** Place labels carry their own: "Freden (Leine)"
    produced フレーデン (ライネ)の聖ラウレンティウス教会.
  * **Category-shaped labels.** ~818 of the corpus name a GROUPING, not a
    building -- "Cultural heritage monuments in X", plural "Synagogues".
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import religious_building_morphemes as m  # noqa: E402


# --------------------------------------------------------------------------
# The place is mandatory -- this is the anti-collision rule
# --------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["ja", "zh", "ko"])
def test_no_place_means_no_label(lang):
    assert m.render("St. Laurentius", "Q16970", lang, place=None) is None, (
        "without a place, hundreds of items share one dedication -- 515 Madonna "
        "churches collapsed onto 聖母教会 when this was allowed"
    )


def test_the_place_disambiguates_two_identical_dedications():
    a = m.render("St. Martin", "Q16970", "ja", place="レーデン")
    b = m.render("St. Martin", "Q16970", "ja", place="ビッセンドルフ")
    assert a and b and a != b


def test_place_goes_first_and_possessive():
    """Emma, 2026-09-17: 'Place first, possessive'."""
    assert m.render("St. Laurentius", "Q16970", "ja",
                    place="レーデン") == "レーデンの聖ラウレンティウス教会"
    assert m.render("St. Laurentius", "Q16970", "zh",
                    place="雷登") == "雷登圣老楞佐教堂"
    assert m.render("St. Laurentius", "Q16970", "ko",
                    place="레덴") == "레덴의 성라우렌시오교회"


def test_a_place_disambiguator_does_not_leak_in():
    got = m.render("St. Laurentius", "Q16970", "ja", place="フレーデン (ライネ)")
    assert got == "フレーデンの聖ラウレンティウス教会", got
    assert "(" not in got and "（" not in got


# --------------------------------------------------------------------------
# Dedication parsing
# --------------------------------------------------------------------------

def test_a_multi_token_saint_is_one_dedicatee():
    got = m.render("San Giovanni Battista", "Q16970", "ja", place="ローマ")
    assert got == "ローマの聖洗礼者ヨハネ教会", got
    assert got.count("ヨハネ") == 1, "John rendered twice"


def test_a_fused_saint_marker_still_gets_the_prefix():
    got = m.render("Igreja de Santiago", "Q16970", "ja", place="リスボン")
    assert got.startswith("リスボンの聖"), got


def test_a_glued_german_compound_is_split():
    got = m.render("St.-Petri-Kirche", "Q16970", "ja", place="レーデン")
    assert got == "レーデンの聖ペトロ教会", got


def test_a_hyphenated_dedication_phrase_is_found():
    """'Notre-Dame' matched nothing until hyphens were normalised; 111 labels."""
    got = m.render("Notre-Dame", "Q16970", "ja", place="パリ")
    assert got == "パリの聖母教会", got


def test_an_unknown_dedicatee_is_refused():
    assert m.render("St. Fictitious", "Q16970", "ja", place="レーデン") is None


# --------------------------------------------------------------------------
# The type comes from P31, never from the label
# --------------------------------------------------------------------------

def test_the_type_comes_from_p31_not_the_label():
    """Two thirds of the corpus carries no English type word, so the label
    cannot be the source of the type."""
    chapel = m.render("St. Laurentius", "Q108325", "ja", place="レーデン")
    church = m.render("St. Laurentius", "Q16970", "ja", place="レーデン")
    assert chapel.endswith("礼拝堂") and church.endswith("教会")


def test_an_unmapped_p31_is_refused():
    assert m.render("St. Laurentius", "Q99999999", "ja", place="レーデン") is None


def test_a_label_naming_the_wrong_type_does_not_win():
    """Label says Chapel, P31 says church building -- P31 wins."""
    got = m.render("St. Laurentius Chapel", "Q16970", "ja", place="レーデン")
    assert got.endswith("教会"), got


# --------------------------------------------------------------------------
# Category-shaped labels are refused
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label", [
    "Cultural heritage monuments in Foo",
    "Synagogues in Nyrsko",
    "Churches in Bavaria",
    "Historic district of Bar",
    "Uspenskoe estate",
])
def test_category_shaped_labels_are_refused(label):
    assert m.is_category_shaped(label), label
    assert m.render(label, "Q16970", "ja", place="レーデン") is None


def test_a_real_building_is_not_mistaken_for_a_category():
    for label in ("St. Laurentius", "San Giovanni Battista", "Notre-Dame"):
        assert not m.is_category_shaped(label), label


# --------------------------------------------------------------------------
# Table sanity
# --------------------------------------------------------------------------

@pytest.mark.parametrize("table", ["TYPES", "NAMES", "DEDICATIONS", "NAME_PHRASES"])
def test_every_table_entry_covers_every_language(table):
    for key, forms in getattr(m, table).items():
        for lang in ("ja", "zh", "ko"):
            assert forms.get(lang), f"{table}[{key!r}] has no {lang}"


def test_markers_and_names_do_not_overlap():
    """A token cannot be both 'saint' and a saint's name, or parsing is
    order-dependent."""
    overlap = set(m.SAINT_MARKERS) & set(m.NAMES)
    assert not overlap, f"token is both a marker and a name: {sorted(overlap)}"


def test_stopwords_and_names_do_not_overlap():
    overlap = set(m.STOPWORDS) & set(m.NAMES)
    assert not overlap, f"token is both a stopword and a name: {sorted(overlap)}"


def test_english_is_not_emitted():
    """Stage 1's English is paused and is not re-derived here."""
    assert m.render("St. Laurentius", "Q16970", "en", place="Freden") is None
