"""Swedish, Norwegian and Danish into katakana — the rest of Emma's "All four".

Asked on 2026-09-20 which of nl/sv/no/da to build for the 492 native-language
long-tail religious buildings, Emma answered **"All four — nl, sv, no, da"**.
Dutch shipped the same day; these are the other three, 119 labels between them.

⛔ **The vocabulary had to come first, and the corpus says why in one number.**
`gamla` — "old" — is the SECOND most common word in the Swedish labels, 27 of 84.
A reading family alone would have emitted 聖ガムラ教会 for `Gamla kyrka`, which is
"the old church". Emma ruled that class the same day — *"Translate the modifier,
like the mosques"* — so the Nordic modifiers are translated, not read.

⚠ These assert the READING against attested Japanese forms where one exists:
Stockholm ストックホルム, Uppsala ウップサラ, Skänninge シェンニンゲ, Björk ビョーク.
A family that disagrees with the attested form is reading something else.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import religious_building_morphemes as m  # noqa: E402
from plain_latin_katakana import (  # noqa: E402
    to_katakana, rules_for_country,
)


# --------------------------------------------------------------------------
# The three vowels
# --------------------------------------------------------------------------
@pytest.mark.parametrize("word,fam,expected", [
    ("Umeå", "sv", "ウメオ"),       # å is オ, and NOT long
    ("Alnö", "sv", "アルネ"),       # ö is エ — Malmö マルメ, not マルモ
    ("Gävle", "sv", "イェヴレ"),    # ä is エ, and g before it palatalises
    ("Vesløs", "da", "ヴェスレス"),  # ø is エ
])
def test_the_extra_vowels(word, fam, expected):
    assert to_katakana(word, fam) == expected


def test_jo_is_the_yo_cluster_not_j_plus_the_folded_vowel():
    """⛔ `jö`/`jø` is /jø/, written ョ. Folded to `e` first, Björk came back
    ビェルク; it is ビョーク, and Mjøndalen ミョンダレン not ミェンダレン."""
    assert to_katakana("Björkskata", "sv") == "ビョルクスカタ"
    assert to_katakana("Mjøndalen", "no") == "ミョンダレン"


# --------------------------------------------------------------------------
# ⛔ Swedish palatalisation, and the velar nasal that must survive it
# --------------------------------------------------------------------------
def test_swedish_palatalises_k_and_g_before_a_front_vowel():
    """This is the one of the three whose palatalisation Japanese convention
    reflects: Göteborg イェーテボリ, Köping シェーピング."""
    assert to_katakana("Falköping", "sv") == "ファルシェピング"
    assert to_katakana("Göteborg", "sv").startswith("イェ")


def test_the_velar_nasal_is_not_a_front_vowel_g():
    """⛔ Swedish `-inge` is /ɪŋɛ/ — the g belongs to the ŋ. The table's
    `ge -> ye` rule cannot see that and Skänninge came back シェンニニェ."""
    assert to_katakana("Skänninge", "sv") == "シェンニンゲ"


def test_norwegian_does_not_palatalise_a_bare_k():
    """⛔ The deliberate difference from Swedish. Norwegian `ki` is /çɪ/, but the
    convention writes it with the k row — Kirkenes is キルケネス, not シルケネス —
    while the Swedish forms above are attested the other way. Only the
    unambiguous DIGRAPHS are palatalised in Norwegian."""
    assert to_katakana("Kirkenes", "no").startswith("キ")
    assert to_katakana("Kjell", "no").startswith("シ")      # kj IS palatal


def test_danish_palatalises_nothing():
    """⛔ Danish `kirke` is /ˈkiɐ̯kə/ — キルケ, not シルケ. Copying the Swedish
    table here would have been the biggest single error available."""
    assert to_katakana("Kirke", "da") == "キルケ"
    assert to_katakana("Køge", "da").startswith("ケ")


# --------------------------------------------------------------------------
# Doubled consonants
# --------------------------------------------------------------------------
def test_doubled_obstruents_take_the_sokuon():
    """Without the geminate set, Uppsala came back ウププサラ — two full プ."""
    assert to_katakana("Uppsala", "sv") == "ウップサラ"
    assert to_katakana("Stockholm", "sv") == "ストックホルム"


def test_a_bare_c_is_readable():
    """`Centrumkyrkan` was the one unreadable Swedish stem: the grid has no c
    row, so without a loan-letter rule the whole word was refused."""
    assert to_katakana("Centrum", "sv") == "セントルム"


# --------------------------------------------------------------------------
# ⛔ The vocabulary, which is the half that stops a modifier becoming a saint
# --------------------------------------------------------------------------
def test_gamla_is_a_modifier_and_not_a_dedicatee():
    """27 of the 84 Swedish labels contain it. Read as a name it is 聖ガムラ."""
    assert "gamla" in m.BUILDING_MODIFIERS
    assert m.BUILDING_MODIFIERS["gamla"]["ja"] == "旧"


@pytest.mark.parametrize("word", [
    "gamle", "gammel", "katolska", "katolsk", "metodist", "baptist",
    "adventist", "kyrkogård", "kirkegård", "slots", "sjömans",
])
def test_the_nordic_modifiers_are_registered(word):
    assert word in m.BUILDING_MODIFIERS


@pytest.mark.parametrize("word", ["hellige", "heliga", "helig", "hellig"])
def test_the_definite_holy_is_a_saint_marker(word):
    """Norwegian `Den hellige Dorotheas kapell` is Saint Dorothea's chapel.
    Without this the name slot got a dedicatee called "hellige"."""
    assert word in m.SAINT_MARKERS


@pytest.mark.parametrize("word", [
    "kyrkan", "kirken", "kapell", "gravkapell", "kyrkoruin", "moské",
])
def test_the_inflected_type_words_are_registered(word):
    """⚠ The definite article is a SUFFIX in these languages, so `kyrkan` is the
    same word as `kyrka` and had to be listed — `Korskyrkan` was read whole."""
    assert word in m.TYPE_WORDS


def test_our_lady_is_translated_not_read():
    """`Vår Frue kirke` is Our Lady's church. Every other language's form of the
    phrase was already in the table; the Nordic and Dutch ones were not, and the
    label came back ヴォル・フルエ教会 instead of 聖母教会."""
    assert m.match_dedication("Vår Frue kirke") == ("generic", "vår frue", [])
    assert m.DEDICATIONS["vår frue"]["ja"] == "聖母"
    assert "vår frue" in m.GENERIC_DEDICATIONS


# --------------------------------------------------------------------------
# ⛔ The compound seam, measured
# --------------------------------------------------------------------------
def test_the_sky_compounds_are_split_before_the_sk_rule_can_see_them():
    """Measured 2026-09-20: 17 Swedish labels have `sk` before a front vowel and
    **16 are `sky` from a compound** — Brukskyrkan, Högåskyrkan, Korskyrkan —
    where the s is the linking s of the first element. Read across the seam,
    `sk` + front is /ɧ/ and swallows it. The type-word split is what makes the
    Swedish table's `sky -> shu` rule safe."""
    assert m._strip_compound_type("Brukskyrkan") == "bruks"
    assert m._strip_compound_type("Korskyrkan") == "kors"
    assert m._strip_compound_type("Betlehemskyrkan") == "betlehems"
    # And the two that are genuinely /ɧ/ keep their sk, because no type word
    # ends them.
    assert m._strip_compound_type("Skänninge") == "skänninge"


# --------------------------------------------------------------------------
# Refusals and the country map
# --------------------------------------------------------------------------
def test_swedish_and_norwegian_letters_refuse_each_other():
    """⚠ The three are told apart by COUNTRY_RULES, not by their letters — no
    and da share æ ø å exactly. What the charsets DO catch is a Swedish word in
    a Norwegian label and the reverse."""
    assert to_katakana("Mjøndalen", "sv") is None      # ø is not Swedish
    assert to_katakana("Gävle", "no") is None          # ä is not Norwegian


@pytest.mark.parametrize("word,fam", [
    ("Kraków", "sv"), ("Třebíč", "no"), ("Straße", "da"), ("Pitié", "sv"),
])
def test_a_word_that_is_not_nordic_is_refused(word, fam):
    assert to_katakana(word, fam) is None


def test_the_country_map():
    assert rules_for_country("Q34") == "sv"
    assert rules_for_country("Q20") == "no"
    assert rules_for_country("Q35") == "da"
    assert rules_for_country("Q55") == "nl"
    # ⚠ Finland is NOT sv. Its labels are 29 of 36 English, so it belongs to the
    # placename path, not to a transliteration family — and a Finnish label read
    # with Swedish rules is the confident-wrong failure, not a gap.
    assert rules_for_country("Q33") is None


# --------------------------------------------------------------------------
# The corpora themselves
# --------------------------------------------------------------------------
@pytest.mark.parametrize("country,fam,least", [
    ("Q34", "sv", 80), ("Q20", "no", 20), ("Q35", "da", 13),
])
def test_every_word_in_the_corpus_is_readable_or_known(country, fam, least):
    """⛔ Run, not quoted: 84/84, 21/21 and 14/14 when this was written.

    A word counts as handled if it is a type word, a stopword, a saint marker or
    a modifier — those are translated — or if the family can read it.
    """
    import json
    import re
    import generate_religious_building_multilang as G
    with open(G.CACHE, encoding="utf-8") as fh:
        cache = json.load(fh)["items"]
    english = re.compile(
        r"\b(church|chapel|cathedral|monastery|synagogue|mosque|basilica|"
        r"abbey|convent|temple|hospital|memorial|monument)\b", re.I)
    unreadable, total = [], 0
    for qid, label in G.source_labels():
        meta = cache.get(qid) or {}
        if (meta.get("p17") != country or m.is_category_shaped(label)
                or not G.building_type(meta, m.TYPES) or english.search(label)):
            continue
        total += 1
        for word in re.split(r"[\s,\-–'’/()\.&]+", label):
            if not word or any(c.isdigit() for c in word):
                continue
            stem = m._strip_compound_type(word)
            if (stem in m.TYPE_WORDS or stem in m.STOPWORDS
                    or stem in m.SAINT_MARKERS or stem in m.BUILDING_MODIFIERS):
                continue
            if to_katakana(stem, fam) is None:
                unreadable.append((label, stem))
    assert total >= least, "the %s corpus has shrunk; re-measure" % fam
    assert not unreadable, "unreadable %s stems: %s" % (fam, unreadable[:10])
