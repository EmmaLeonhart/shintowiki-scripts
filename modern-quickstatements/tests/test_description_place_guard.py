"""A description may only name a place it can prove the item is in.

Measured 2026-09-13 against the staged `description_adds.txt`. `infer_templates`
picks the MODAL description in a language's corpus as the generic, and in five
languages the modal one names a city:

    fr  x127  "temple bouddhiste à Kyoto, au Japon"
    es  x 71  "templo budista en Yokohama, Japón"
    pl  x 41  "świątynia buddyjska w Jokohamie w Japonii"
    it  x 41  "tempio buddista a Yokohama, Giappone"
    cs  x 25  "buddhistický chrám v japonském městě Jokohama"

The generic is stamped on every target with no resolved prefecture, so those
became claims about items that are somewhere else. Of eight sampled `à Kyoto`
items, three are in Tokushima, Fukushima and Mie. The existing class-specificity
guard checks the template says WHAT the item is; nothing checked that it does not
also say WHERE, falsely. 328 such lines were live in the drip and are stripped.

The `{pref}` template is a different case and stays: it fills from the item's own
P131, so the place it names is the item's.

⚠ **WHAT THIS DOES NOT CATCH, stated because the gap is real.** The test is a
frequency one — a capitalised token in a minority of DISTINCT descriptions is a
place name — and it cannot see a place that is in *every* description. German is
exactly that: its prefecture template came out
`"Shinto-Schrein in Sammu, Präfektur {pref}, Japan"`, with a city in Chiba baked
into the frame, and 75 of 104 staged de lines named Sammu for items in 30
different prefectures. The corpus itself is poisoned, so no self-referential test
can see it. Those 75 lines are stripped by hand and the general fix — a place
vocabulary read from the corpus items' own P131 labels rather than inferred from
capitalisation — is queued, not pretended at.
"""

import importlib.util
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)


def _mod():
    if MQ not in sys.path:
        sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        "_t_desc_adds", os.path.join(MQ, "generate_description_adds.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FR = ["temple bouddhiste à Kyoto, au Japon",
      "temple bouddhiste à Tokyo, au Japon",
      "temple bouddhiste à Osaka, au Japon",
      "temple bouddhiste à Nara, au Japon",
      "temple bouddhiste au Japon"]


def test_a_city_in_the_generic_is_found():
    mod = _mod()
    places = mod.place_tokens(FR, "temple bouddhiste")
    assert "Kyoto" in places and "Osaka" in places, places
    assert mod.names_a_place(FR[0], {}, places) == "Kyoto"


def test_the_country_is_not_a_place_token():
    """It is in nearly every description, which is what marks it as the frame.
    Flagging it would drop every generic in every language."""
    mod = _mod()
    places = mod.place_tokens(FR, "temple bouddhiste")
    assert "Japon" not in places, places
    assert mod.names_a_place("temple bouddhiste au Japon", {}, places) is None


def test_a_german_class_word_is_not_a_place():
    """German capitalises every noun, so "Tempel" scores like a place name. The
    first version of this flagged the perfectly good generic "buddhistischer
    Tempel in Japan" and would have left de with no description at all."""
    mod = _mod()
    de = ["buddhistischer Tempel in Japan",
          "buddhistischer Tempel in Kyoto, Japan",
          "buddhistischer Tempel in Osaka, Japan",
          "buddhistischer Tempel in Nara, Japan"]
    places = mod.place_tokens(de, "buddhistischer Tempel")
    assert "Tempel" not in places, places
    assert mod.names_a_place("buddhistischer Tempel in Japan", {}, places) is None


def test_a_prefecture_key_is_found_even_when_frequency_misses_it():
    """The two vocabularies are complementary: the 47 prefecture keys are known
    outright, the corpus supplies the cities."""
    mod = _mod()
    assert mod.names_a_place("sanctuaire shinto dans la préfecture de Nagano",
                             {"Nagano": "préfecture de Nagano"}, set()) == "Nagano"


def test_both_templates_are_checked_not_just_the_generic():
    """The pref template is substituted only at the prefecture key, so any OTHER
    place in the modal description survives into every filled line."""
    src = open(os.path.join(MQ, "generate_description_adds.py"), encoding="utf-8").read()
    body = src[src.index("places = place_tokens("):src.index("targets = targets_with_pref(")]
    assert 'names_a_place(gen,' in body, "the generic is no longer checked"
    assert 'replace("{pref}", "")' in body, (
        "the prefecture template is no longer checked with its slot removed")


def test_the_staged_file_has_no_surviving_false_location():
    """The seven groups measured against their items' real P131 on 2026-09-13.
    Their absence is the check that the strip actually happened and that a later
    regeneration did not put them back."""
    path = os.path.join(MQ, "description_adds.txt")
    if not os.path.exists(path):
        import pytest
        pytest.skip("not generated in this checkout")
    text = io.open(path, encoding="utf-8").read()
    for lang, needle in (("fr", "à Kyoto, au Japon"),
                         ("es", "en Yokohama, Japón"),
                         ("pl", "w Jokohamie w Japonii"),
                         ("it", "a Yokohama, Giappone"),
                         ("cs", "městě Jokohama"),
                         ("de", "Sammu")):
        offenders = [i for i, l in enumerate(text.splitlines(), 1)
                     if re.match(rf'^Q\d+\|D{lang}\|', l) and needle in l]
        assert not offenders, (
            f"{lang} lines naming {needle!r} are back at {offenders[:3]} — these "
            "assert a location their items do not have")
