"""Punctuation and abbreviation gaps in the label parser (2026-09-19).

Found by classifying the 909 German-family labels the pipeline still refused.
Every one of these refused a label whose dedicatee the table knows perfectly
well — `Laurentius`, `Bonifatius`, `Nikolaus`, `Bartholomeus` — over a bracket,
a quotation mark or a missing space.

⛔ The reason they were invisible until now: the transliteration fallback refuses
the WHOLE label when one token cannot be read, so a token like `(wuppertal)`
does not degrade the output, it deletes it. Before the fallback existed these
labels were refused anyway for having an unknown name, so the bracket cost
nothing and left no trace.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import religious_building_morphemes as m  # noqa: E402

CHURCH = "Q16970"


def ja(label, place="P", place_en=None):
    return m.render(label, CHURCH, "ja", place=place, rules=None,
                    latin_rules="de", place_en=place_en)


# --------------------------------------------------------------------------
# The trailing and mid-label disambiguator
# --------------------------------------------------------------------------
def test_a_trailing_disambiguator_is_not_part_of_the_name():
    assert ja("St. Laurentius (Wuppertal)",
              place_en="Wuppertal") == "Pの聖ラウレンティウス教会"


def test_a_nested_disambiguator():
    """`(Selters (Westerwald))` — one level of nesting is common enough that
    `[^()]*` was not enough."""
    head, qual, _ = m._dedicatee_split("St. Bonifatius (Selters (Westerwald))")
    assert head == ["bonifatius"]
    assert "westerwald" in qual and "selters" in qual


def test_a_mid_label_disambiguator_too():
    """⚠ An end-anchored rule left these refused over the same bracket:
    `Taschenberg (Uckerland) church`, `Wegkapelle (Badanhausen) Nord`."""
    head, qual, _ = m._dedicatee_split("Taschenberg (Uckerland) church")
    assert head == ["taschenberg"] and qual == ["uckerland"]


def test_the_disambiguator_is_a_qualifier_not_a_dedicatee():
    """It goes in the qualifier slot, so `_echoes_place` can drop it when it is
    simply the town the item already sits in."""
    out = ja("St. Nikolaus (Rodau (Vogtland))", place_en="Rodau")
    assert out == "Pのフォグトラントの聖ニコラオス教会"


# --------------------------------------------------------------------------
# Abbreviations and glued markers
# --------------------------------------------------------------------------
def test_a_marker_glued_to_its_name_by_a_period():
    """`St.Bartholomeus` — no space. Splitting on the period generally would
    break `St.` itself, so only a marker glued to a word is separated."""
    assert ja("St.Bartholomeus") == "Pの聖バルトロマイ教会"


def test_sta_is_a_saint_marker():
    """`Sta. Maria (Sulzbach)` was losing its 聖 to a dedicatee called `sta`."""
    assert "sta" in m.SAINT_MARKERS
    head, _, saw = m._dedicatee_split("Sta. Maria (Sulzbach)")
    assert head == ["maria"] and saw


@pytest.mark.parametrize("word", ["ev.", "luth.", "kath.", "dr.", "hl."])
def test_german_abbreviations_are_frame(word):
    assert word in m.STOPWORDS


def test_german_quotation_marks_are_stripped():
    """`Krankenhauskirche „Maria Heil der Kranken“` reached the transliterator
    as `„maria` and failed the allowed-letters check — the whole label refused
    over a punctuation mark."""
    head, _, _ = m._dedicatee_split('Kirche „Maria Heil der Kranken“')
    assert "maria" in head and not any(t.startswith("„") for t in head)


# --------------------------------------------------------------------------
# What must still be refused
# --------------------------------------------------------------------------
@pytest.mark.parametrize("label", [
    "Klosterkirche Bronnbach at night",
    "St. Laurentius (Wuppertal) at night",
])
def test_a_photograph_is_not_a_building(label):
    """⚠ These two emitted ニグフト for `night` the moment the bracket stopped
    refusing them outright. A photo's category is not a label for the building."""
    assert ja(label) is None


@pytest.mark.parametrize("label", ["Krankenhauskapelle", "Anstaltskirche",
                                   "Hospitalkirche"])
def test_a_hospital_chapel_is_not_named_after_a_hospital(label):
    """`Krankenhauskapelle` emitted クランケンハウス教会 — the German for the
    thing `hospital` was already blocked as in English.

    ⚠ NARROWED 2026-09-19, hours later, when Emma ruled that a setting IS
    translated. A hospital chapel is 病院 + type, never the reading of the word
    `Krankenhaus`. The `hospital` reading is what this test was written to stop
    and it is still stopped."""
    assert m._dedicatee_split(label)[0] == []
    out = ja(label)
    assert out is None or "クランケンハウス" not in out
    if m.building_modifiers(label):
        assert out and "病院" in out


def test_bartholomeus_resolves_to_the_table():
    assert m.NAMES["bartholomeus"] == m.NAMES["bartholomew"]
