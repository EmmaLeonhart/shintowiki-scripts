"""Propagating a corrected English label into the other languages.

Emma 2026-08-04: "replacing all of the wrong names ... not just the english one.
It's wrong in French and Indonesian too." The non-English labels were built FROM
the English ones, so a bad reading was copied outward and fixing only en leaves
the item inconsistent with itself.

What is asserted here is mostly the ways a naive substring swap goes wrong. Every
case below was a real defect in the first run of the generator.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
ROOT = os.path.dirname(MQ)
for p in (MQ, os.path.join(ROOT, "shinto_miraheze")):
    if p not in sys.path:
        sys.path.insert(0, p)

# These rebind sys.stdout at module scope; hold every wrapper so the first one
# collected cannot close the buffer under the others (see the Ise creates test).
_KEEP_STDOUT_ALIVE = [sys.stdout]
import generate_multilingual_label_fixes as gen  # noqa: E402
_KEEP_STDOUT_ALIVE.append(sys.stdout)
import direct_daily_edits as dde  # noqa: E402
_KEEP_STDOUT_ALIVE.append(sys.stdout)

OUT = os.path.join(MQ, "multilingual_label_fixes.txt")


def fr(label, old, new, old_suf="", new_suf=""):
    return gen.rewrite(label, old, new, old_suf, new_suf, "fr")


def test_file_is_registered_with_the_drip():
    assert "multilingual_label_fixes.txt" in dde.ATOMIC_FILES


def test_every_committed_line_parses():
    for line in open(OUT, encoding="utf-8"):
        if line.strip():
            assert dde.parse_qs_line(line.strip()), line


def test_no_japanese_label_is_ever_rewritten():
    # The ja label is what everything else is derived from.
    for line in open(OUT, encoding="utf-8"):
        if line.strip():
            lang = line.split("|")[1][1:]
            assert lang not in gen.SKIP_LANGS, line


def test_label_without_the_old_name_is_left_alone():
    # A language that TRANSLATED the name rather than transliterating it carries
    # nothing to fix, and must not be touched.
    assert fr("sanctuaire de Kumano", "Samugawa", "Samukawa") is None


def test_elision_drops_when_the_new_name_starts_with_a_consonant():
    # "sanctuaire d’Hikida" -> the new name begins T, so d’ must become de.
    assert fr("sanctuaire d’Hikida", "Hikida",
              "Tsukudanimasu Hitokotoneko") == \
        "sanctuaire de Tsukudanimasu Hitokotoneko"


def test_elision_appears_when_the_new_name_starts_with_a_vowel():
    assert fr("sanctuaire de Samugawa", "Samugawa", "Iitama") == \
        "sanctuaire d’Iitama"


def test_macron_vowels_keep_the_elision():
    # The first-run bug: Ō was not in the vowel set, so "d’Oominakami" was
    # turned into "de Ōminakami".
    assert fr("sanctuaire d’Oominakami", "Oominakami", "Ōminakami") == \
        "sanctuaire d’Ōminakami"


def test_y_does_not_take_an_elision():
    # The other first-run bug: Y is a consonant sound here, and treating it as a
    # vowel turned "sanctuaire de Yagiri" into "d’Yakiri".
    assert fr("sanctuaire de Yagiri", "Yagiri", "Yakiri") == \
        "sanctuaire de Yakiri"


def test_article_is_untouched_when_the_vowel_class_does_not_flip():
    # Rewriting whenever anything changed is what produced "d’Yasui Kompira"
    # from a label whose name had not changed at all.
    assert fr("sanctuaire de Yasui Kompira-gu", "Yasui Kompira",
              "Yasui Kompira", "-gu", "-gū") == \
        "sanctuaire de Yasui Kompira-gū"


def test_generic_suffix_is_corrected_even_when_the_name_is_identical():
    assert fr("Kuil Yasui Kompira-gu", "Yasui Kompira", "Yasui Kompira",
              "-gu", "-gū") == "Kuil Yasui Kompira-gū"


def test_suffix_survives_when_the_two_english_labels_punctuate_it_differently():
    # 岡田宮 went from "Okagagū" to "Okada-gū". Matching only "-gū" leaves the old
    # stem as the whole of "Okagagū", so the French label lost its gū entirely.
    old_stem, old_suf = gen.split_label("Okagagū")
    new_stem, new_suf = gen.split_label("Okada-gū")
    assert old_stem == "Okaga" and new_stem == "Okada"
    # The gū survives, and it comes back punctuated the way the corrected English
    # label punctuates it rather than the way the broken one did.
    assert fr("sanctuaire d'Okagagū", old_stem, new_stem, old_suf, new_suf) == \
        "sanctuaire d'Okada-gū"


def test_split_label_leaves_a_short_name_intact():
    # Stripping must never eat the name itself.
    assert gen.split_label("Ise Shrine") == ("Ise", " Shrine")
    assert gen.split_label("Jinja")[0] == "Jinja"


def test_hikida_survives_as_an_alias_in_all_three_languages():
    # 疋田神社 (ひきだ) is a real alternative name for 調田坐一事尼古神社 — it was only
    # ever wrong as the PRIMARY label. Emma 2026-08-04.
    staged = {l.strip() for l in open(OUT, encoding="utf-8") if l.strip()}
    assert 'Q22119431|Aen|"Hikida Shrine"' in staged
    assert 'Q22119431|Afr|"sanctuaire d’Hikida"' in staged
    assert 'Q22119431|Aid|"Kuil Hikida"' in staged


def test_aliases_are_a_hand_kept_list_not_a_rule():
    # Aliasing every replaced label would preserve the misreadings too —
    # "Samugawa" for 寒川 is simply wrong and must not survive as an alias.
    assert set(gen.ALIASES) == {"Q22119431"}
