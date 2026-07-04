"""Temple-only tier (2026-07-04): nn, ceb, mai, as, ur — languages whose
Wikidata conventions exist for temples but not shrines. Per Emma's
standardization rule, the temple word serves BOTH kinds where the language
has no shrine word (ceb/mai/as/ur); nn has distinct words like its nb
sibling. gan/cdo/zh-mo were deliberately routed to the CJK path instead
(kanji copy, no transliteration); pa/km/lo/dz/new/mad/shn deferred — no
script converter / no derivable convention."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import ALL_LANGS, format_label  # noqa: E402
import language_registry as r  # noqa: E402


def test_in_all_langs_and_registry():
    for lang in ["nn", "ceb", "mai", "as", "ur"]:
        assert lang in ALL_LANGS, f"{lang} missing from ALL_LANGS"
        assert lang in r.COVERED, f"{lang} missing from language_registry"


def test_nn_mirrors_nb_with_nynorsk_words():
    assert format_label("nn", "Kasuga", False, "shrine") == "Kasuga-heilagdomen"
    assert format_label("nn", "Kasuga", False, "temple") == "Kasuga-tempel"


def test_ceb_templong_prefix_both_kinds():
    assert format_label("ceb", "Itsukushima", False, "shrine") == "Templong Itsukushima"
    assert format_label("ceb", "Itsukushima", False, "temple") == "Templong Itsukushima"


def test_mai_devanagari_mandir_both_kinds():
    # same transliteration as hi, same word for both kinds
    assert format_label("mai", "Kasuga", False, "shrine") == "कसुग मंदिर"
    assert format_label("mai", "Kasuga", False, "temple") == "कसुग मंदिर"


def test_as_bengali_script_with_assamese_ra():
    label = format_label("as", "Kasuga", False, "shrine")
    assert label == "কাসুগা মন্দিৰ"
    assert label == format_label("as", "Kasuga", False, "temple")
    # the Assamese ra must appear in the word, the Bengali ra must not
    assert "ৰ" in label and "র" not in label


def test_as_ra_substitution_in_name():
    # a name whose transliteration carries ra: Bengali র → Assamese ৰ
    label = format_label("as", "Hirano", False, "shrine")
    assert label is not None
    assert "র" not in label


def test_ur_perso_arabic_mandir_both_kinds():
    label = format_label("ur", "Kasuga", False, "shrine")
    assert label == "کاسوگا مندر"
    assert label == format_label("ur", "Kasuga", False, "temple")
