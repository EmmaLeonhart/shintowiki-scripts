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


def test_the_target_must_be_in_japan():
    """Every generic this script can infer names Japan, because the corpus is
    Japan-shaped. The Buddhist-temple class already filtered on P17; the
    Shinto-shrine class did not, so overseas shrines were being described as being
    in Japan.

    Measured 2026-09-13 over the 819 staged `bangunan kuil di Jepang` lines: 325 in
    Japan, **98 demonstrably not** (Taiwan 62, Korea under Japanese rule 10, PRC 7,
    Manchukuo 3, USA 3, Palau, Thailand, San Marino), 397 with no P17 at all. The
    colonial-era shrines are the bulk — Changchun, Hsinking, Keijō, Karenkō.
    """
    src = open(os.path.join(MQ, "generate_description_adds.py"), encoding="utf-8").read()
    body = src[src.index("def targets_with_pref("):src.index("def langs_with_label_no_desc(")
               if "def langs_with_label_no_desc(" in src[src.index("def targets_with_pref("):]
               else len(src)]
    q = body[body.index("SELECT ?item ?l"):body.index('"""', body.index("SELECT ?item ?l"))]
    assert "?item wdt:P17 wd:Q17" in q, (
        "the target query no longer requires the item to be in Japan; overseas "
        "shrines get a description saying they are")


def test_the_country_filter_is_not_on_the_shared_class_list():
    """CLASSES is shared with the label pipeline, and a LABEL asserts no country.
    Filtering there would drop legitimate label work to fix a description bug."""
    fixes = open(os.path.join(MQ, "generate_description_fixes.py"), encoding="utf-8").read()
    block = fixes[fixes.index("CLASSES = ["):fixes.index("]", fixes.index("CLASSES = ["))]
    assert '("Q845945", "")' in block, (
        "the Shinto-shrine class in the SHARED list grew a country filter — that "
        "belongs on this script's targets, not on the labels")


def test_the_corpus_is_not_country_filtered_either():
    """Template inference wants every existing description it can see; narrowing
    the corpus would shrink the evidence for no gain."""
    src = open(os.path.join(MQ, "generate_description_adds.py"), encoding="utf-8").read()
    corpus = src[src.index("def desc_corpus("):src.index("def targets_with_pref(")]
    assert "wdt:P17" not in corpus, (
        "desc_corpus grew a country filter; it should read every description")


def test_the_country_survives_inflection():
    """⛔ The country is what has to score HIGH in place_tokens, and in an
    inflecting language it is spelled differently in each description — Японія /
    Японії / Японією — so no single form clears a majority and the country reads
    as a place name.

    The first version counted exact tokens and did exactly that: it dropped
    "буддійський храм в Японії" (uk), "buddhista templom Japánban" (hu) and
    "Βουδιστικός ναός στην Ιαπωνία" (el), leaving three languages with no
    description at all. That is a guard blocking the work it was added to protect.
    """
    mod = _mod()
    uk = ["синтоїстське святилище в Японії",
          "буддійський храм в Японії",
          "храм у префектурі Шімане, Японія",
          "святилище у префектурі Нара, Японія",
          "святилище в Японію"]
    places = mod.place_tokens(uk, "буддійський храм")
    assert not any(p.startswith("Япон") for p in places), places
    assert mod.names_a_place("буддійський храм в Японії", {}, places) is None
    # and the real place names are still found
    assert mod.names_a_place("храм у префектурі Шімане, Японія", {}, places) == "Шімане"


def test_a_city_is_still_caught_after_the_stemming_change():
    """The stem is four characters, which must not be so coarse that a city
    collapses into the frame."""
    mod = _mod()
    places = mod.place_tokens(FR, "temple bouddhiste")
    assert {"Kyoto", "Osaka", "Tokyo"} <= places, places
    assert mod.names_a_place(FR[0], {}, places) == "Kyoto"


def test_the_prefecture_slot_is_filled_with_the_key_not_the_full_label():
    """⛔ infer_templates cuts the template at the KEY ("Shizuoka"), so the
    template keeps the generic word: "kuil Shinto di Prefektur {pref}, Jepang".
    Filling that with the full label "Prefektur Shizuoka" doubles it.

    Measured in the 2026-09-13 regeneration this was found in: ~600 lines came out
    "di Prefektur Prefektur Shizuoka" (id), "v prefekturi Prefektura Kjoto" (sl),
    "у префектурі Префектура Шімане" (uk). A regression from the same change that
    gave this script pref_keys — before it the template was cut at the full label,
    so filling with the full label matched.
    """
    src = open(os.path.join(MQ, "generate_description_adds.py"), encoding="utf-8").read()
    body = src[src.index("proposals = {}"):src.index("by_pair = defaultdict(list)")]
    assert "label_to_key" in body, (
        "the prefecture slot is filled from the raw label again; the generic word "
        "doubles")
    assert 'pref_t.replace("{pref}", slot)' in body


def test_a_skip_says_which_check_emptied_it():
    """46 languages printed "no place-free template" in one run when most of them
    simply had no inferable template at all — a cause attached without checking."""
    src = open(os.path.join(MQ, "generate_description_adds.py"), encoding="utf-8").read()
    assert "no template could be inferred" in src
    assert "the place guard dropped it" in src
